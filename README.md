# Forza Horizon Series Custom Fonts .ttf to .vfont 

This is Reverse Engineering for Forza Horizon Series Custom Fonts **.vfont** (**.ttf** convert to **.vfont**)

### How to use

### Install **[Python](https://www.python.org/downloads/)**

Open Command Prompt / CMD

Install fonttools

**`pip install fonttools`**

Convert .ttf to .vfont

**`python ttf2vfont.py YourFonts.ttf Anthem_A.vfont --template Anthem_A.vfont_original`**


The **`--template`** argument specifies the source **`.vfont`** file to be used as a template; the script will copy its header and utilize the same character set expected by the game. It is highly recommended to always include this.

If omitted, the script will default to using Latin characters, punctuation, and currency symbols—or you can define a custom set using **`--chars`** or **`--all`**.

If **Your Fonts** appear wider or taller than the condensed "Anthem" font, try using **`--scale 0.85`**.

You can also adjust the ascent and descent values ​​using the **`--ascent`** and **`--descent`** arguments.



**Supported**
- **Forza Horizon 2** ✅
- Forza Horizon 3 (Wait for the next update)
- Forza Horizon 4 (Wait for the next update)
- Forza Horizon 5 (Wait for the next update)
- Forza Horizon 6 (Wait for the next update)
