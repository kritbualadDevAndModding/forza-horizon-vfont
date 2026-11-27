# Forza Horizon / Motorsport Series Custom Fonts .ttf to .vfont 

This is Reverse Engineering for Forza Horizon / Motorsport Series Custom Fonts **.vfont** (**.ttf** convert to **.vfont**)
___
### How to use

### Install **[Python](https://www.python.org/downloads/)**

Open Command Prompt / CMD

Install fonttools

**`pip install fonttools`**

Convert .ttf to .vfont
___
### Forza Horizon 2
**`python FH2ttf2vfont.py YourFonts.ttf YourFonts.vfont`**
___
### Forza Horizon 3
**`python make_onebatch.py YourFonts.ttf Anthem_A.vfont YourFonts.vfont --all`**
___
### Forza Horizon 4 / 5
**`python FH4FH5ttf2vfont.py YourFonts.ttf YourFonts.vfont --template Horizon_A.vfont --name Horizon_A --all`**
___
The **`--template`** argument specifies the source **`.vfont`** file to be used as a template; the script will copy its header and utilize the same character set expected by the game. It is highly recommended to always include this.
___
If omitted, the script will default to using Latin characters, punctuation, and currency symbols—or you can define a custom set using **`--chars`** or **`--all`**.

### *Example*
for **all**

**`--all`** = to include all Unicode characters.

or

**`--chars "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,:;!?-/"`** = for using custom Unicode text as want
___
If **Your Fonts** appear wider or taller than the condensed "Anthem" font, try using **`--scale 0.85`**.

You can also adjust the ascent and descent values ​​using the **`--ascent`** and **`--descent`** arguments.

Asset Font Forza Horizon Series
___
### Forza Horizon 2/3 vfont
- Anthem_A = Black Condensed
- Anthem_B = ... 
- Anthem_C = ... 
- Anthem_D = ... 
___
### Forza Horizon 4/5/6 vfont
- Horizon_A = Black Condensed
- Horizon_B = ... 
- Horizon_C = ... 
- Horizon_D = ... 
___
**Supported**
- **Forza Motorsport 5 (Azimuth Only)** ✅ **(Use FH2)**
- **Forza Motorsport 6 (Azimuth Only)**  ❌ **(The zip file is encrypted.)**
- **Forza Horizon 2 (Azimuth Only)** ✅
- **Forza Horizon 3 (Azimuth Only)** ✅
- **Forza Horizon 4 (Steam Only)** ✅
- **Forza Horizon 5** ✅
- Forza Horizon 6 (Wait for the next update)
