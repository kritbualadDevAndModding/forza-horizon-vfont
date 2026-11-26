# Forza Horizon / Motorsport Series Custom Fonts .ttf to .vfont 

This is Reverse Engineering for Forza Horizon / Motorsport Series Custom Fonts **.vfont** (**.ttf** convert to **.vfont**)

### How to use

### Install **[Python](https://www.python.org/downloads/)**

Open Command Prompt / CMD

Install fonttools

**`pip install fonttools`**

Convert .ttf to .vfont

### Forza Horizon 2
**`python FH2ttf2vfont.py YourFonts.ttf YourFonts.vfont`**

### Forza Horizon 3
**`python make_onebatch.py YourFonts.ttf Anthem_A.vfont YourFonts.vfont --all`**


The **`--template`** argument specifies the source **`.vfont`** file to be used as a template; the script will copy its header and utilize the same character set expected by the game. It is highly recommended to always include this.

If omitted, the script will default to using Latin characters, punctuation, and currency symbols—or you can define a custom set using **`--chars`** or **`--all`**.

If **Your Fonts** appear wider or taller than the condensed "Anthem" font, try using **`--scale 0.85`**.

You can also adjust the ascent and descent values ​​using the **`--ascent`** and **`--descent`** arguments.

Asset Font Forza Horizon Series

### Forza Horizon 2/3 vfont
- Anthem_A = Black Condensed
- Anthem_B = ... 
- Anthem_C = ... 
- Anthem_D = ... 

### Forza Horizon 4/5/6 vfont
- Horizon_A = Black Condensed
- Horizon_B = ... 
- Horizon_C = ... 
- Horizon_D = ... 

**Supported**
- Forza Motorsport 5 (Wait for the next update)
- Forza Motorsport 6 (Wait for the next update)
- **Forza Horizon 2 (Azimuth Only)** ✅
- **Forza Horizon 3 (Azimuth Only)** ✅
- Forza Horizon 4 (Wait for the next update)
- Forza Horizon 5 (Wait for the next update)
- Forza Horizon 6 (Wait for the next update)
