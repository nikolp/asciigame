"""Simple ASCII arcade style game using curses.

    Copyright 2019, Philip Nikolov

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import curses
import time
import math
import random

# How often to redraw the screen
FRAMES_PER_SECOND = 10
# This is how much health a new object will have by default when created.
DEFAULT_INITIAL_HEALTH = 5
# What is the most health the player can have. Need a fixed value so we can
# draw the "health bar" on screen in consistent way.
PLAYER_HEALTH_MAX = DEFAULT_INITIAL_HEALTH
# How long it takes for the player's laser gun to reload in between shots.
LASER_RELOAD_TIME_SEC = 0.5
# After game is won or lost, for how many seconds to show the
# "game over" or "game won" banner before the program exits.
GAMEWINORLOSE_WAIT = 3
# How many enemies to create at the beginning of the game.
# Once all are destroyed, you win.
ENEMIES_INITIAL_COUNT = 6


class EdgeStrategy(object):
  """What to do when you reach edge of screen."""
  # Quietly disappear from the scene
  DISAPPEAR = 0
  # Bounce in opposite direction as if hitting a wall
  BOUNCE = 1


class Model(object):
  """Base class for objects that can be placed in the game.

  The division of responsibility between Model and the derived MultiCharObj
  is far from clean. But mostly the goal of Model is to handle the "physics"
  such as movement, collision detection and MultiCharObj to handle display
  aspects meaning how to draw yourself properly. Since every interesting object
  would have to be drawn, the objects array that you see in the main event loop
  should be all MultiCharObj.
  TODO: consider making this class abstract.
  """
  def __init__(self):
    self.set_radius(0, 0)
    self.set_position(None, None)
    self.set_speed(0)
    self.set_direction(1, 1)
    self.set_edge_strategy(EdgeStrategy.BOUNCE)
    self.set_can_collide(True)
    self.set_z_index(1)
    self.set_health(DEFAULT_INITIAL_HEALTH)
    self.set_damage(1)
    self.set_label('')

  def set_label(self, l):
    """See documentation of RunCollisionDetection() how to use 'label'."""
    self.label = l

  def set_damage(self, d):
    """How much damage does this object do, when it hits something else."""
    self.damage = d

  def set_health(self, h):
    """How much health does this object have? Its health may be diminished
    through collissions or perhaps passage of time, etc.
    Once health reaches zero, object will be removed from the game.
    """
    self.health = h

  def set_z_index(self, z):
    """Can be set to any integer.
    If two objects occupy the same space, the one
    with the higher z index will be the one displayed. If they have
    exactly same z index, one of them will show, but no guarantee which one.
    """
    self.z_index = z

  def set_radius(self, x_radius, y_radius):
    """Specifies the dimensions of the object. See more about this in
    MultiCharObj. Basically the object is a box of width = 2*x_radius + 1 chars
    and height = 2*y_radius + 1 characters.
    TODO: Make this private or protected. End-users of this class would
    typically not call this directly, but specify the strings that need to be
    printed to display this object. From the size of those strings, dimensions
    can be derived. (See the MultiCharObj constructor)
    """
    self.x_radius = x_radius
    self.y_radius = y_radius

  def set_position(self, x, y):
    """Sets coordinates of the middle of the object.
    Note: we use the curses coordinate system where (0,0) is the leftmost
    top position on the screen. x increases to the right. y increases downwards.
    Note: for smoother movement
    we track this position using floating point numbers, and convert to integer
    only when it is time to actually draw it on the discrete ascii screen.
    TODO: Perhaps rename to set_initial_position() as the way the physics
    engine is designed now, future (x, y) are computed from current (x, y)
    and current velocity. So in theory, one should NOT hack (x, y) directly.
    But who knows, maybe we will add a teleportation option in which case
    set_position would become needed again :)
    """
    self.x = x
    self.y = y

  def set_speed(self, speed):
    """Like in physics, sets the absolute value of speed. Measured in characters
    per cycle, i.e. number of discrete char spaces object will move during one
    frame.
    TODO: Make it more "absolute" so it is not impacted by frame rate. Right
    now if you increase FRAMES_PER_SECOND, the game speeds up. In theory,
    one should simply increase FRAMES_PER_SECOND for a smoother response time
    and rendering experience, (if the computer can handle it) and objects
    should continue moving at previous observable pace. So speed should
    really be measured as chars positions per second, not per frame.
    """
    self.saved_speed = speed
    self.speed = speed

  def set_direction(self, x, y):
    """Sets which way the velocity vector is pointing and adjusts
    the x and y components of speed so that the total speed is self.speed
    Thus if you want to go right set_direction(1, 0) and set_direction(2, 0)
    are identical, they point in same direction. Same with this digonal right
    and down instruction: set_direction(1, 1) vs set_direction(2, 2)
    """
    direction_len = math.sqrt(x*x+y*y)
    if direction_len < 0.001:
      raise ValueError("Bad direction, vector size too small: {}, {}".format(
          x, y))
    self.x_speed = self.speed * x / direction_len
    self.y_speed = self.speed * y / direction_len

  def stop(self):
    """Stop moving by setting your x and y speed to zero.
    But remember your speed right before stopping, so you can properly resume.
    """
    self.x_speed_save = self.x_speed
    self.x_speed = 0.0
    self.y_speed_save = self.y_speed
    self.y_speed = 0.0

  def resume(self):
    """Continue moving after a stop."""
    if abs(self.x_speed) + abs(self.y_speed) > 0.0:
      # Nothing to do, was already moving
      return
    self.x_speed, self.y_speed = self.x_speed_save, self.y_speed_save

  def x_in_bounds(self, x, screen_width):
    """Returns if the object is in the given x position, would it
    still fully fit in the screen horizontally."""
    return ((0 <= x - self.x_radius) and
            (x + self.x_radius <= screen_width - 1))

  def y_in_bounds(self, y, screen_height):
    """Returns if the object is in the given  position, would it
    still fully fit in the screen vertically."""
    return ((0 <= y - self.y_radius) and
            (y + self.y_radius <= screen_height - 1))

  def propose_move(self, x, y, x_speed, y_speed):
    """Proposes what should be the new x, y positions.

    Args:
      current position and current speed
    Returns:
      proposed new position as an (x, y) tuple
    """
    return x+x_speed, y+y_speed

  def move(self, screen_height, screen_width):
    """Computes and sets the new x and y coordinates.

    Args:
      the screen dimensions, in order to determine object has left the area
    Returns:
      False: if object should disappear from game
      True: in all other cases
    """
    # While 0 is a very reasonable default speed, there is no reasonable
    # default value for object coordinates. Ensure they were explicitly set.
    if self.x is None or self.y is None:
      raise RuntimeError("Initial position not set. Did you forget to call"
                         " set_position()?")
    # Where should I be next?
    x, y = self.propose_move(self.x, self.y, self.x_speed, self.y_speed)
    # If will be out of bounds, switch direction -now- or disappear -forever-
    x_inside = self.x_in_bounds(x, screen_width)
    y_inside = self.y_in_bounds(y, screen_height)
    if not (x_inside and y_inside):
      if self.edge_strategy == EdgeStrategy.DISAPPEAR:
        return False
    # If got here, object is either completely fine, or of it is not,
    # it must "bounce". This is achieved by reversing the x or y direction
    # of movement.
    if not x_inside:
      self.x_speed = -self.x_speed
    if not y_inside:
      self.y_speed = -self.y_speed
    # Where will I be, now that I have switched direction of movement?
    self.x, self.y = self.propose_move(
        self.x, self.y, self.x_speed, self.y_speed)
    # If this is still off, serious error
    if not self.x_in_bounds(self.x, screen_width):
      raise RuntimeError("Bad x: {}. Speed was {}.".format(
          self.x, self.x_speed))
    if not self.y_in_bounds(self.y, screen_height):
      raise RuntimeError("Bad y: {}. Speed was {}.".format(
          self.y, self.y_speed))
    return True

  def set_edge_strategy(self, strategy):
    """See the EdgeStrategy class documentation."""
    self.edge_strategy = strategy

  def set_can_collide(self, collide):
    """See the docs for HaveObjectsCollided()"""
    self.can_collide = collide


class MultiCharObj(Model):
  """The graphical representation of an object in the game.

  For our sanity when doing rendering and collision detection, prefer every
  object to have a rectangular shape and have a well defined "middle" i.e.
  "center" cell.
  The rest of the object extends symmetrically from that middle.
  The distance from middle to right-most (and left-most) edge is x_radius.
  The distance from middle to top-most (and bottom-most) edge is y_radius.
  Here is an example object, rendered
XXX1XXX
321M123
XXX1XXX
  Notice the center/middle cell labeled M.
  There's one step to the top/bottom from M so y_radius is 1.
  There are 3 steps to the leftmost/rightmost edge from M so x_radius is 3.
  The ASCII strings required to render the object are passed into the constructor
  as a list. In this case it would be [
"XXX1XXX",
"321M123",
"XXX1XXX",
]
  Of course spaces are also allowed so another object of same dimensions may be
"   1   ",
"321M123",
"  -1-  ",
  But as far as collission detection / likelihoold to be hit by laser,
  they are the same.
  """
  def __init__(self, x_radius, y_radius, strings):
    super(MultiCharObj, self).__init__()
    if len(strings) != 2*y_radius + 1:
      raise ValueError(
          "strings[] array unexpected length: {} expect {} because y radius {}"
          .format(len(strings), 2*y_radius+1, y_radius))
    for string in strings:
      if len(string) != 2*x_radius + 1:
        raise ValueError(
          "string unexpected length: {} expect {} because x radius {}".format(
              len(string), 2*x_radius + 1, x_radius))
    self.set_radius(x_radius, y_radius)
    self.strings = strings

  def draw(self, stdscr):
    """Executes the actual curses command to display object on console.

    Args:
      stdscr: handle to the curses-provided screen object
    """
    center_y, center_x = int(round(self.y)), int(round(self.x))
    for i in range(2 * self.y_radius + 1):
      try:
        stdscr.addstr(center_y - self.y_radius + i,
                      center_x - self.x_radius, self.strings[i])
      except Exception as e:
        raise e


class Ball(MultiCharObj):
  """Convenience class for objects that are exactly one character big."""
  def __init__(self, char):
    super(Ball, self).__init__(0, 0, [char])


class Enemy(MultiCharObj):
  """A martian.

  While Model, MultiCharObj, Ball are fairly generic, this class is quite
  specific to the needs of this game.
  """
  def __init__(self, x_radius, y_radius, strings):
    super(Enemy, self).__init__(x_radius, y_radius, strings)
    self.set_shoot_interval(0.0)

  def set_shoot_interval(self, t):
    """How often the object is allowed to shoot, in seconds (float)
    Set to 0.0 if you want it to stop shooting for a long time.
    Set it back to positive value if you want it to start up again.
    """
    self.shoot_interval = t
    self.last_shot = time.time()

  def try_to_shoot(self):
    """Whenever allowed to do so, shoot.

    Returns:
      The laser/bomb/rocket whatever projectile object just got created.
      None if no shot happened.
    """
    if self.shoot_interval == 0.0:
      return None
    if time.time() > self.last_shot + self.shoot_interval + random.uniform(
        -1, 1):
      self.last_shot = time.time()
      bomb = Ball('|')
      bomb.set_label('BOMB')
      bomb.set_health(1)
      bomb.set_position(self.x, self.y+self.y_radius+1)
      bomb.set_speed(1)
      bomb.set_direction(0, 1)
      bomb.set_edge_strategy(EdgeStrategy.DISAPPEAR)
      return bomb
    return None


class TankPlayer(MultiCharObj):
  """The main player.

  While Model, MultiCharObj, Ball are fairly generic, this class is quite
  specific to the needs of this game.
  """
  def __init__(self, x_radius, y_radius, strings):
    super(TankPlayer, self).__init__(x_radius, y_radius, strings)
    self.laser_shot_time = 0

  def shoot_laser(self):
    """Attempts to shoot laser. May fail if laser gun is still reloading,
    or out of ammo, etc.

    Returns:
      The laser projectile object that just got shot (if shot success)
      None (if shot failure)
    """
    time_now = time.time()
    if time_now < self.laser_shot_time + LASER_RELOAD_TIME_SEC:
      return None
    self.laser_shot_time = time_now
    laser = Ball('/')
    laser.set_label('B')
    # Start the laser a bit above you, don't want to shoot yourself.
    laser.set_position(self.x + 2, self.y - 2)
    laser.set_speed(1.5)
    laser.set_direction(1,-1)
    laser.set_edge_strategy(EdgeStrategy.DISAPPEAR)
    return laser


def HaveObjectsCollided(a, b):
  """Checks if two objects in the scene have collided.

  Args:
    a: Model
    b: Model

  Returns: True if the two objects have collided

  Always returns False if either object is of the "non collidable" kind.
  This is determined by the "can_collide" property of the object.
  For example, set can_collide=False for a cloud that you want planes
  to fly through, without hitting it. In this demo game, we set
  can_collide=False for messages that appear on the screen.
  """
  if not (a.can_collide and b.can_collide):
    return False
  a_x = int(round(a.x))
  a_y = int(round(a.y))
  b_x = int(round(b.x))
  b_y = int(round(b.y))
  # Definitely not a collision if
  # 1. Leftmost part of a is to the right of rightmost part of b
  if a_x - a.x_radius > b_x + b.x_radius:
    return False
  # 2. Rightmost part of a is to the left of leftmost part of b
  if a_x + a.x_radius < b_x - b.x_radius:
    return False
  # 3. Bottom of a is above top of b
  if a_y - a.y_radius > b_y + b.y_radius:
    return False
  # 4. Top of a is below bottom of b
  if a_y + a.y_radius < b_y - b.y_radius:
    return False
  # If got there, there must be overlap
  return True


def RunCollisionDetection(objects):
  """Checks all the given objects for pair-wise collisions.

  This is brute force O(N^2) check of every objects against every
  other object. But with the optimizaton of not doing both (A,B) and
  (B,A) check. The "label" concept carries important caveat.
  Two objects with the same label are not allowed to collide.
  For example two martians, if they accidentally crash into each
  other, we prefer not to count it as a crash and just let them
  merrily go through each other. Or if we had two players, we
  would give them the same "label", so they don't take away
  health from each other if they touch through the course of the game.
  Every objects has "health" and "damage" properties.
  "health" intuitively is how much health you have.
  "damage" is how much you bumping into somebody would detract
  from their health. This method performs the health subtraction
  for the collissions it detects.

  Returns: None
  """
  i = 0
  while i < len(objects):
    j = i+1
    while j < len(objects):
      oi, oj = objects[i], objects[j]
      if HaveObjectsCollided(oi, oj) and (oi.label != oj.label):
        oi.health -= oj.damage
        oj.health -= oi.damage
      j += 1
    i += 1


def RemoveDeadObjects(objects):
  """Goes over the objects array to prune dead objects.

  Returns:
    (Potentially empty) set of objects that got removed.
  """
  removed_set = set()
  i = 0
  while i < len(objects):
    obj = objects[i]
    if obj.health <= 0:
      del objects[i]
      removed_set.add(obj)
      # Compensate for the fact that upon deletion i should not really increment
      i -= 1
    i += 1
  return removed_set


def UpdatePlayerHealth(player, player_health_obj):
  """Sets the right number of X characters to indicate current player health.

  Args:
    player: the player object
    player_health_obj: the health display object.

  For example if player.health == 1, the health_object will display X,
  if player.health == 2, then 2 health bars such as XX will show, etc.
  """
  max_health = len(player_health_obj.strings[0])
  player_health_obj.strings = [
      'X' * player.health + ' ' * (max_health - player.health)]


def MakePlayer():
  """Initializes and returns the main player object."""
  player = TankPlayer(3, 1, ["    // ",
                             "BBBBBB ",
                             "CCCCCCC"])
  player.set_label('P')
  player.set_speed(0.5)
  player.set_direction(1, 0)
  return player


def MakePlayerHealthObject(player_health_max):
  """Makes a very basic player health object, but does not fully
  plug it into the game framework.
  Pulled out into separate method to aid testing.

  Args:
    player_health_max: int, maximum health a player can have
  Returns:
    The right-sized MultiCharObj
  """
  return MultiCharObj(int(player_health_max/2), 0,
                      ['X'*player_health_max])


def MakeAndInstallPlayerHealthObject(player, objects, player_health_max):
  """Initializes the objects that display player health and inserts
  them into objects array.
  There are two separate objects. One is just a static label that says
  HEALTH =
  The second one is a dynamic object that will show X or XX or XXX etc
  depending on how much health the player object currently has.

  Args:
    player: so that player's initial health can be obtained
    objects: the list of all objects where the new ones will be added
    player_health_max: int, the most health a player can have. This needs
    to be an odd integer, as it will drive the width in characters of
    the player health object.

  Returns:
    A handle to the dynamic object as we need to keep updating it
  during the event loop.
  """
  if not isinstance(player_health_max, int):
    raise TypeError("player_health_max must be int, got: {}".format(
        player_health_max))
  if player_health_max % 2 == 0:
    raise ValueError("player_health_max must be an odd integer, but got: {}".
                     format(player_health_max))

  label = MultiCharObj(4, 0, ["HEALTH = "])
  label.set_position(4, 0)
  label.set_can_collide(False)
  objects.append(label)

  player_health = MakePlayerHealthObject(player_health_max)
  player_health.set_position(12, 0)
  player_health.set_can_collide(False)
  player_health.set_z_index(3)
  objects.append(player_health)
  return player_health


def MakeGameOver():
  """Initializes and returns the 'Game Over' object to display if you lose."""
  game_over = MultiCharObj(4, 3,
                          [
"/\    /\ ",
"\/    \/ ",
"  /--\   ",
"  |\/|   ",
"  |/\|   ",
"   --    ",
"YOU LOSE ",
                           ])
  game_over.set_z_index(3)
  game_over.set_can_collide(False)
  return game_over


def MakeGameWin():
  """Initializes and returns the object banner to displayed if you win."""
  game_win = MultiCharObj(5, 0, ["GAME WIN ;D"])
  game_win.set_z_index(3)
  game_win.set_can_collide(False)
  return game_win


def MakeEnemies(num_enemies, screen_width, screen_height):
  """Creates num_enemies objects and returns them as a set.

  Args:
    num_enemies: how many
    screen_width, screen_height: screen dimensions so that the martians
    are placed within the bounds of the game area.

  Returns:
    set of the created enemies
  """
  enemies = set()
  for _ in range(num_enemies):  # Create this many martians
    # Randomly pick among two different styles of martian
    if random.randint(0, 1) == 0:
      m = Enemy(1, 1, [
          " A ",
          "(0)",
          "III"])
    else:
      m = Enemy(4, 3, [
"    A    ",
"   AAA   ",
"  | \" |  ",
"__| O |__",
"   Y Y   ",
"   | |   ",
"   | |   ",
])
    # Initial placement is random, but make sure you are not too close
    # to any edge, especially the top edge.
    m.set_position(
        screen_width/2 + random.randint(
            int(-screen_width/3), int(screen_width/3)),
        max(screen_height/3 + random.randint(
            int(-screen_height/4), int(screen_height/4)),
            m.y_radius+1))
    m.set_speed(0.7)
    # Don't let it collides with another 'M' object i.e. another martian
    m.set_label('M')
    # Set a small speed "downward" so that martians can keep approaching
    # the player who is at bottom of screen. Remember the note further up
    # about coordinate system.
    y_speed = 0.05
    if random.randint(0, 1) == 0:
      m.set_direction(-1.0, y_speed)
    else:
      m.set_direction(+1.0, y_speed)
    m.set_shoot_interval(2)
    enemies.add(m)

  return enemies


def HandleKeyPress(player, objects, key):
  """Check in non-blocking way if any key is pressed and react accordingly.

  Args:
    player: the main player object, so that if a key press relates to player
  action, that behavior can be triggered
    objects: the list of all objects present in the game, so that if
  a new object is created in this handler, it can be added to the list
    key: the character that got pressed, represented as int

  Returns:
    True if game should immediately end because "Q"uit was pressed.
    False in all other cases.
  """
  try:
    ch = chr(key).lower()   # Canonicalize to lower case string of length 1
  except ValueError:
    # Something way out of ascii range, just ignore
    return False
  if ch == 'q':
    # Quit the game
    return True
  elif ch == 'a':
    # Go left
    player.resume()
    player.set_direction(-1, 0)
  elif ch == 'd':
    # Go right
    player.resume()
    player.set_direction(1, 0)
  elif ch == 's':
    # Stop in place
    player.stop()
  elif ch == ' ':
    laser = player.shoot_laser()
    if laser:
      objects.append(laser)
  elif ch == 'r':
    # Shoot a rocket
    b = MultiCharObj(1, 1, [" A ",
                            "( )",
                            "( )"])
    b.set_position(player.x-2, player.y-3)
    b.set_label('R')
    b.set_speed(1)
    b.set_direction(0,-1)
    b.set_edge_strategy(EdgeStrategy.DISAPPEAR)
    objects.append(b)
  elif ch == 'p':
    # Pause the game to enter interactive pdb debugger
    import pdb; pdb.set_trace()
  return False


def main(stdscr):
  screen_width, screen_height = curses.COLS, curses.LINES
  exit_time = float('inf')

  stdscr.nodelay(True)  # makes getch() non blocking
  curses.curs_set(0)    # cursor invisible

  # List of all currently visible and alive objects in the game
  objects = []
  player = MakePlayer()
  player.set_position(3, screen_height - 4)
  objects.append(player)
  player_health = MakeAndInstallPlayerHealthObject(
      player, objects, PLAYER_HEALTH_MAX)
  game_over_sign = MakeGameOver()
  game_over_sign.set_position(screen_width/2, screen_height/2)
  game_win_sign = MakeGameWin()
  game_win_sign.set_position(screen_width/2, screen_height/2)
  enemies = MakeEnemies(ENEMIES_INITIAL_COUNT, screen_width, screen_height)
  objects.extend(list(enemies))
  game_has_ended = False

  while True:
    # Anything crashed into anything else, such as got hit by a laser?
    # If so, subract from their health accordingly.
    RunCollisionDetection(objects)

    dead = RemoveDeadObjects(objects)
    enemies = enemies.difference(dead)  # Keep the alive ones only

    if not game_has_ended:
      # Are we dead or are all our enemies dead?
      if player in dead:
        game_has_ended = True
        objects.append(game_over_sign)
      if len(enemies) == 0:
        game_has_ended = True
        objects.append(game_win_sign)
      if game_has_ended:
        # Leave a few seconds for human to read message on screen
        # before really exiting to command line
        # In the mean time, game loop will run a few more times.
        exit_time = time.time() + GAMEWINORLOSE_WAIT

    # Show how much health the protagonist has remaining.
    UpdatePlayerHealth(player, player_health)

    # Anybody who is allowed to shoot a projectile, now is the time.
    for enemy in enemies:
      projectile = enemy.try_to_shoot()
      if projectile:
        objects.append(projectile)

    # Attempt to move each objects.
    # Delete the ones that have left the screen boundaries.
    i = 0
    while i < len(objects):
      object_stays_on_screen = objects[i].move(screen_height, screen_width)
      if not object_stays_on_screen:
        del objects[i]
      if object_stays_on_screen:
        # Only increment i if there was no deletion performed,
        # otherwise we would be skipping over an object.
        i += 1

    # Begin repainting by first clearing the canvas.
    stdscr.clear()

    # Draw objects still alive
    for obj in sorted(objects, key=lambda x: x.z_index):
      obj.draw(stdscr)

    # Repaint screen: not neded, see below
    # stdscr.refresh()
    # Documentation say this will naturally call stdscr.refresh()
    key_press = stdscr.getch()
    exit_game_immediately = HandleKeyPress(player, objects, key_press)
    if exit_game_immediately:
      return 0

    time.sleep(1.0 / FRAMES_PER_SECOND)

    if time.time() > exit_time:
      return 0

if __name__ == '__main__':
  curses.wrapper(main)
