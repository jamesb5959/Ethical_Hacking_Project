use std::{
    fs::OpenOptions,
    io::{self, Write},
    time::Duration,
};
use crossterm::{
    event::{self, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use tui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout},
    style::{Color, Style},
    text::{Span, Spans},
    widgets::{Block, Borders, Paragraph},
    Terminal,
};
use serde::{Deserialize, Serialize};
use reqwest::blocking::Client;
use serde_json::Value;

#[derive(PartialEq)]
enum InputMode {
    Normal,
    Insert,
}

#[derive(Serialize)]
struct GenerateRequest {
    prompt: String,
}

#[derive(Debug, Deserialize)]
struct GenerateResponse {
    response: String,
}

struct App {
    input: String,
    history: Vec<(String, String)>,
    input_mode: InputMode,
    scroll: u16,
}

impl App {
    fn new() -> Self {
        Self {
            input: String::new(),
            history: Vec::new(),
            input_mode: InputMode::Normal,
            scroll: 0,
        }
    }

    fn send_prompt(&mut self) {
        if self.input.trim().is_empty() {
            return;
        }
        let client = Client::builder().timeout(None).build().unwrap();
        let request = GenerateRequest {
            prompt: self.input.clone(),
        };
        let res = client
            .post("http://localhost:5000/generate")
            .json(&request)
            .send();

        match res {
            Ok(resp) => {
                let status = resp.status();
                if status.is_success() {
                    if let Ok(parsed) = resp.json::<GenerateResponse>() {
                        self.history.push((self.input.clone(), parsed.response.clone()));
                    } else {
                        self.history.push((self.input.clone(), "Malformed success response.".into()));
                    }
                } else {
                    let err_text = resp.json::<Value>()
                        .ok()
                        .and_then(|v| v.get("error").and_then(|e| e.as_str()).map(String::from))
                        .unwrap_or_else(|| format!("Server returned {}", status));
                    self.history.push((self.input.clone(), format!("Error: {}", err_text)));
                }
            }
            Err(e) => {
                self.history.push((self.input.clone(), format!("Request failed: {}", e)));
            }
        }
        append_to_csv(&self.input, &self.history.last().unwrap().1);
        self.input.clear();
        // reset scroll to top
        self.scroll = 0;
    }
}

fn append_to_csv(prompt: &str, response: &str) {
    if let Ok(mut wtr) = OpenOptions::new().create(true).append(true).open("chat_history.csv") {
        // Escape double quotes by doubling them for CSV
        let p = prompt.replace('"', "\"\"");
        let r = response.replace('"', "\"\"");
        let _ = write!(wtr, "\"{}\",\"{}\"\n", p, r);
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;
    let mut app = App::new();

    let res = run_app(&mut terminal, &mut app);

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;
    if let Err(e) = res {
        eprintln!("Error: {:?}", e);
    }
    Ok(())
}

fn run_app<B: tui::backend::Backend>(
    terminal: &mut Terminal<B>,
    app: &mut App,
) -> io::Result<()> {
    loop {
        terminal.draw(|f| {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .margin(1)
                .constraints([Constraint::Min(5), Constraint::Length(3), Constraint::Length(1)])
                .split(f.size());

            // build history lines
            let mut lines: Vec<Spans> = Vec::new();
            for (user, resp) in &app.history {
                lines.push(Spans::from(vec![
                    Span::styled("You: ", Style::default().fg(Color::Blue)),
                    Span::raw(user.clone()),
                ]));
                for (i, line) in resp.lines().enumerate() {
                    if i == 0 {
                        lines.push(Spans::from(vec![
                            Span::styled("Gemma: ", Style::default().fg(Color::Green)),
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
                    Span::styled("q", Style::default().fg(Color::Red)),
                    Span::raw(" to quit. Use ↑/↓ to scroll."),
                ]),
                InputMode::Insert => Spans::from(vec![
                    Span::raw("Type your prompt. "),
                    Span::styled("Enter", Style::default().fg(Color::Green)),
                    Span::raw(" to send, "),
                    Span::styled("Esc", Style::default().fg(Color::Red)),
                    Span::raw(" to cancel."),
                ]),
            });
            f.render_widget(help, chunks[2]);
        })?;

        if event::poll(Duration::from_millis(200))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    // scrolling
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
                // input handling
                match key.code {
                    KeyCode::Char('i') if app.input_mode == InputMode::Normal => {
                        app.input_mode = InputMode::Insert;
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
                    KeyCode::Esc if app.input_mode == InputMode::Insert => {
                        app.input.clear();
                        app.input_mode = InputMode::Normal;
                    }
                    KeyCode::Char(c) if app.input_mode == InputMode::Insert => {
                        app.input.push(c);
                    }
                    KeyCode::Backspace if app.input_mode == InputMode::Insert => {
                        app.input.pop();
                    }
                    _ => {}
                }
            }
        }
    }
}
