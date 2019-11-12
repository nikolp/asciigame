# asciigame
Game inspired by [Space Invaders](https://en.wikipedia.org/wiki/Space_Invaders). It is written in Python and implemented with [ASCII graphics](https://en.wikipedia.org/wiki/ASCII_art).

Note this is not a general purpose game engine. Feel free to make a similar (or different) game via copying the file and editing it to your needs (while honoring the license).

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
* Health: watch the "HEALTH" bar located in top left section of the screen. When it reaches zero, you lose.

# Dependencies:
* Python 3
* Requires presence of the [curses](https://docs.python.org/3/howto/curses.html) library which is usually pre-installed.
* Should run in any Linux, ChromeOS, MacOS shell. (Not on Windows where Python curses does not work out of the box.)

# To grok:
* You may want to start in main() to get a sense for the game event loop.
* But eventually you will have to read everything.

# To test:
* Ensure your default python is python 3.3 or higher
* python game_test.py

# Exercises to modify the code in increasing order of difficulty:
* Change ENEMIES_INITIAL_COUNT to 10, save, run this more challenging version.
* Edit the strings that represent the tank or the martians.
* Change the edge_strategy for the various lasers and bombs from DISAPPEAR to BOUNCE and wreak havoc on the scene!
* Notice how time.time() is used to ensure the player does not fire lasers too often. Introduce the same logic for Rockets.
* Read the various documentation for "label" property of objects. Given the code as is, do you think a bomb sent by a martian 
can hurt another martian? Try to test it out by creating two martians, one above the other, with speed 0 so that they stay put.
Does the bottom one die?
* Introduce "regeneration" logic where your player can gain back some of the lost health through the passage of time.
* Write more unit tests for all helper functions and place them in game_test.py
Note: main() is the most difficult to test as its core functionality is not to compute and return something, but to produce side effects (painting various chars on the screen). How would you test it in an automated way?
