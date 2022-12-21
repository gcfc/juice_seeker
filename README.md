# juice_seeker
Find available EV charger ports in my office, and email me if there are any.

Turns out I can pass the "I'm not a robot" recaptcha at login (robustly!) with a bit of web scraping in python and the [Houndify API](https://www.houndify.com/) for speech recognition. That's pretty cool I guess.

## Requirements

```python
python3 -m pip install -r requirements.txt
```

For Mac users:
1. Install Homebrew and add this line to `.zshrc` (Mac only)
```bash
eval $(/opt/homebrew/bin/brew shellenv)
```
2. Using Homebrew, install `flac` and `ffmpeg`. 
```bash
brew install flac
brew install ffmpeg
```

Must install the equivalent `flac` and `ffmpeg` packages for other OS's. Might involve a few extra lines of code too.
