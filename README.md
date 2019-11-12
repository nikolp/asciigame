# asciigame
Game inspired by [Space Invaders](https://en.wikipedia.org/wiki/Space_Invaders). It is written in Python and implemented with [ASCII graphics](https://en.wikipedia.org/wiki/ASCII_art).

# To run:
* Download the single-file source code game.py
* cd to that directory
* python game.py
   
# Game instructions:
* A: start moving left. Will keep moving until you press "S" or "D". Do not keep it pressed as that registers as multiple "key press" events and may make the game laggy.
* S: stop
* D: start moving right. Same caveats as "A".
* Space: shoot a laser
* R: shoot a rocket
* Q: quit the game

# Dependencies:
* Python 3
* Requires presence of the [curses](https://docs.python.org/3/howto/curses.html) library which is usually pre-installed.
* Should run in any Linux, ChromeOS, MacOS shell. (Not on Windows where Python curses does not work out of the box.)


