use std::{
    env, fs,
    fs::OpenOptions,
    io::{self, Write},
    time::Duration,
};

use crossterm::{
    event::{self, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use tui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout},
    style::{Color, Style},
    text::{Span, Spans},
    widgets::{Block, Borders, Paragraph},
    Terminal,
};

const DEFAULT_API_URL: &str = "http://localhost:5000/generate";

#[derive(PartialEq)]
enum InputMode {
    Normal,
    Insert,
    UploadPath,
}

#[derive(Serialize)]
struct GenerateRequest {
    prompt: String,
}

#[derive(Serialize)]
struct SaveMemoryRequest {
    prompt: String,
    response: String,
    kind: String,
}

#[derive(Serialize)]
struct UploadMemoryRequest {
    filename: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct GenerateResponse {
    response: String,
}

#[derive(Debug, Deserialize)]
struct ErrorResponse {
    error: String,
}

struct App {
    input: String,
    history: Vec<(String, String)>,
    input_mode: InputMode,
    scroll: u16,
    client: Client,
    api_url: String,
}

impl App {
    fn new() -> Result<Self, reqwest::Error> {
        let api_url = env::var("GEMMA_API_URL").unwrap_or_else(|_| DEFAULT_API_URL.to_string());
        let client = Client::builder().timeout(None).build()?;

        Ok(Self {
            input: String::new(),
            history: Vec::new(),
            input_mode: InputMode::Normal,
            scroll: 0,
            client,
            api_url,
        })
    }

    fn send_prompt(&mut self) {
        let prompt = self.input.trim().to_string();
        if prompt.is_empty() {
            return;
        }

        let request = GenerateRequest {
            prompt: prompt.clone(),
        };
        let response_text = match self.client.post(&self.api_url).json(&request).send() {
            Ok(resp) => parse_response(resp),
            Err(e) => format!("Request failed: {}", e),
        };

        append_to_csv(&prompt, &response_text);
        self.history.push((prompt, response_text));
        self.input.clear();
        self.scroll = 0;
    }

    fn memory_url(&self, path: &str) -> String {
        format!(
            "{}{}",
            self.api_url
                .strip_suffix("/generate")
                .unwrap_or(&self.api_url),
            path
        )
    }

    fn save_latest_memory(&mut self) {
        let Some((prompt, response)) = self.history.last().cloned() else {
            self.history.push((
                "Save memory".to_string(),
                "No conversation response to save yet.".to_string(),
            ));
            return;
        };

        let request = SaveMemoryRequest {
            prompt,
            response,
            kind: "workflow".to_string(),
        };

        let message = match self
            .client
            .post(self.memory_url("/memory/save"))
            .json(&request)
            .send()
        {
            Ok(resp) if resp.status().is_success() => {
                "Saved latest response to Weaviate.".to_string()
            }
            Ok(resp) => parse_response(resp),
            Err(e) => format!("Save failed: {}", e),
        };
        self.history.push(("Save memory".to_string(), message));
    }

    fn upload_file_memory(&mut self) {
        let path = self.input.trim().to_string();
        if path.is_empty() {
            return;
        }

        let message = match fs::read_to_string(&path) {
            Ok(content) => {
                let request = UploadMemoryRequest {
                    filename: path.clone(),
                    content,
                };
                match self
                    .client
                    .post(self.memory_url("/memory/upload"))
                    .json(&request)
                    .send()
                {
                    Ok(resp) if resp.status().is_success() => {
                        format!("Uploaded {} to Weaviate.", path)
                    }
                    Ok(resp) => parse_response(resp),
                    Err(e) => format!("Upload failed: {}", e),
                }
            }
            Err(e) => format!("Could not read {}: {}", path, e),
        };

        self.history.push(("Upload file".to_string(), message));
        self.input.clear();
        self.scroll = 0;
    }
}

fn parse_response(resp: reqwest::blocking::Response) -> String {
    let status = resp.status();
    if status.is_success() {
        return match resp.json::<GenerateResponse>() {
            Ok(parsed) => parsed.response,
            Err(e) => format!("Malformed success response: {}", e),
        };
    }

    let err_text = resp
        .json::<ErrorResponse>()
        .map(|parsed| parsed.error)
        .unwrap_or_else(|_| format!("Server returned {}", status));

    format!("Error: {}", err_text)
}

fn append_to_csv(prompt: &str, response: &str) {
    match OpenOptions::new()
        .create(true)
        .append(true)
        .open("chat_history.csv")
    {
        Ok(mut wtr) => {
            let p = prompt.replace('"', "\"\"");
            let r = response.replace('"', "\"\"");
            let _ = writeln!(wtr, "\"{}\",\"{}\"", p, r);
        }
        Err(e) => eprintln!("Failed to write chat history: {}", e),
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;
    let mut app = App::new()?;

    let res = run_app(&mut terminal, &mut app);

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;
    if let Err(e) = res {
        eprintln!("Error: {:?}", e);
    }
    Ok(())
}

fn run_app<B: tui::backend::Backend>(terminal: &mut Terminal<B>, app: &mut App) -> io::Result<()> {
    loop {
        terminal.draw(|f| {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .margin(1)
                .constraints([
                    Constraint::Min(5),
                    Constraint::Length(3),
                    Constraint::Length(1),
                ])
                .split(f.size());

            let mut lines: Vec<Spans> = Vec::new();
            for (user, resp) in &app.history {
                lines.push(Spans::from(vec![
                    Span::styled("You: ", Style::default().fg(Color::Blue)),
                    Span::raw(user.clone()),
                ]));
                for (i, line) in resp.lines().enumerate() {
                    if i == 0 {
                        lines.push(Spans::from(vec![
                            Span::styled("Sydney: ", Style::default().fg(Color::Green)),
                            Span::raw(line.to_string()),
                        ]));
                    } else {
                        lines.push(Spans::from(Span::raw(format!("    {}", line))));
                    }
                }
                lines.push(Spans::from(Span::raw("")));
            }
            let hist_height = chunks[0].height as usize;
            let max_scroll = lines.len().saturating_sub(hist_height);
            let scroll = app.scroll.min(max_scroll as u16);

            let history = Paragraph::new(lines)
                .block(Block::default().title("Conversation").borders(Borders::ALL))
                .scroll((scroll, 0));
            f.render_widget(history, chunks[0]);

            let input = Paragraph::new(app.input.as_ref())
                .block(Block::default().title("Your Prompt").borders(Borders::ALL))
                .style(Style::default().fg(Color::Yellow));
            f.render_widget(input, chunks[1]);

            let help = Paragraph::new(match app.input_mode {
                InputMode::Normal => Spans::from(vec![
                    Span::raw("Press "),
                    Span::styled("i", Style::default().fg(Color::Green)),
                    Span::raw(" to insert, "),
                    Span::styled("s", Style::default().fg(Color::Green)),
                    Span::raw(" to save latest, "),
                    Span::styled("u", Style::default().fg(Color::Green)),
                    Span::raw(" to upload file, "),
                    Span::styled("q", Style::default().fg(Color::Red)),
                    Span::raw(" to quit. Use Up/Down to scroll."),
                ]),
                InputMode::Insert => Spans::from(vec![
                    Span::raw("Type your prompt. "),
                    Span::styled("Enter", Style::default().fg(Color::Green)),
                    Span::raw(" to send, "),
                    Span::styled("Esc", Style::default().fg(Color::Red)),
                    Span::raw(" to cancel."),
                ]),
                InputMode::UploadPath => Spans::from(vec![
                    Span::raw("Type a text file path. "),
                    Span::styled("Enter", Style::default().fg(Color::Green)),
                    Span::raw(" to upload, "),
                    Span::styled("Esc", Style::default().fg(Color::Red)),
                    Span::raw(" to cancel."),
                ]),
            });
            f.render_widget(help, chunks[2]);
        })?;

        if event::poll(Duration::from_millis(200))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Up => {
                        if app.scroll > 0 {
                            app.scroll -= 1;
                        }
                        continue;
                    }
                    KeyCode::Down => {
                        app.scroll = app.scroll.saturating_add(1);
                        continue;
                    }
                    _ => {}
                }

                match key.code {
                    KeyCode::Char('i') if app.input_mode == InputMode::Normal => {
                        app.input_mode = InputMode::Insert;
                    }
                    KeyCode::Char('s') if app.input_mode == InputMode::Normal => {
                        app.save_latest_memory();
                    }
                    KeyCode::Char('u') if app.input_mode == InputMode::Normal => {
                        app.input.clear();
                        app.input_mode = InputMode::UploadPath;
                    }
                    KeyCode::Char('q') if app.input_mode == InputMode::Normal => {
                        return Ok(());
                    }
                    KeyCode::Enter if app.input_mode == InputMode::Insert => {
                        if !app.input.trim().is_empty() {
                            app.send_prompt();
                        }
                        app.input_mode = InputMode::Normal;
                    }
                    KeyCode::Enter if app.input_mode == InputMode::UploadPath => {
                        app.upload_file_memory();
                        app.input_mode = InputMode::Normal;
                    }
                    KeyCode::Esc
                        if app.input_mode == InputMode::Insert
                            || app.input_mode == InputMode::UploadPath =>
                    {
                        app.input.clear();
                        app.input_mode = InputMode::Normal;
                    }
                    KeyCode::Char(c)
                        if app.input_mode == InputMode::Insert
                            || app.input_mode == InputMode::UploadPath =>
                    {
                        app.input.push(c);
                    }
                    KeyCode::Backspace
                        if app.input_mode == InputMode::Insert
                            || app.input_mode == InputMode::UploadPath =>
                    {
                        app.input.pop();
                    }
                    _ => {}
                }
            }
        }
    }
}
