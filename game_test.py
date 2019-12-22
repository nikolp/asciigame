"""Unit tests for game.py"""
import unittest
from unittest import mock
import game


class ModelTest(unittest.TestCase):
  def testMoveFailsIfSetPositionWasNotCalled(self):
    screen_width, screen_height = 50, 30
    obj = game.Model()
    with self.assertRaisesRegex(RuntimeError, "set_position"):
      obj.move(screen_width, screen_height)


class MultiCharObjTest(unittest.TestCase):
  def testConstructorFailsOnInconsistentYRadius(self):
    with self.assertRaisesRegex(ValueError, "y radius"):
      game.MultiCharObj(0, 5, ["F"])

  def testConstructorFailsOnInconsistentXRadius(self):
    with self.assertRaisesRegex(ValueError, "x radius"):
      game.MultiCharObj(1, 1,
                        ["FOO",
                         "FOO",
                         "FO",   # Mistake on this line.
                        ])


class TankPlayerTest(unittest.TestCase):
  def testShootLaserNothingHappensIfNotEnoughTimeHasPassed(self):
    player = game.MakePlayer()
    player.set_position(10, 10)
    self.assertIsNotNone(player.shoot_laser(), 'First shot should just work')
    self.assertIsNone(player.shoot_laser(),
                      'Shooting too soon after previous should should not work')

  @mock.patch.object(game.time, 'time', autospec=True)
  def testShootLaserWorksIfEnoughTimeHasPassed(self, mock_time):
    player = game.MakePlayer()
    player.set_position(10, 10)
    mock_time.return_value = 1.0
    self.assertIsNotNone(player.shoot_laser(), 'First shot should just work')
    # But now, have to be patient... Let's fast forward time...
    mock_time.return_value += (game.LASER_RELOAD_TIME_SEC + 0.1)
    self.assertIsNotNone(player.shoot_laser())


class HaveObjectsCollidedTest(unittest.TestCase):
  def testObjectsFarAwayNoCollission(self):
    a = game.Ball('X')
    a.set_position(1.0, 1.0)
    b = game.Ball('O')
    b.set_position(5.0, 5.0)
    self.assertEqual(False, game.HaveObjectsCollided(a, b))

  def testCollissionDetectedForSmallObjectsEvenIfCoordinatesNotIdentical(self):
    a = game.Ball('X')
    a.set_position(1.0, 1.0)
    b = game.Ball('O')
    b.set_position(1.2, 1.3)
    self.assertEqual(True, game.HaveObjectsCollided(a, b))


class RunCollisionDetectionTest(unittest.TestCase):
  def MakeTwoCollidingObjects(self):
    a = game.Ball('X')
    a.set_position(1.0, 1.0)
    b = game.Ball('O')
    b.set_position(1.0, 1.0)
    return a, b

  def testNoCollissionHealthStaysSame(self):
    a = game.Ball('X')
    a.set_position(1.0, 1.0)
    a.set_damage(1)
    b = game.Ball('O')
    b.set_position(5.0, 5.0)
    b_previous_health = b.health

    game.RunCollisionDetection([a, b])

    self.assertEqual(b_previous_health, b.health, "B health should not change.")

  def testYesCollissionButSameLabelHealthStaysSame(self):
    a, b = self.MakeTwoCollidingObjects()
    a.set_label("L")
    a.set_health(10)
    a.set_damage(1)
    b.set_label("L")
    b.set_health(5)
    b.set_damage(2)

    game.RunCollisionDetection([a, b])

    self.assertEqual(10, a.health, "A's health should not change.")
    self.assertEqual(5, b.health, "B's health should not change.")

  def testYesCollissionButDifferentLabelHealthDecreasesRightAmount(self):
    a, b = self.MakeTwoCollidingObjects()
    a.set_label("SOME LABEL")
    a.set_health(10)
    a.set_damage(1)
    b.set_label("DIFFERENT LABEL")
    b.set_health(5)
    b.set_damage(2)

    game.RunCollisionDetection([a, b])

    self.assertEqual(8, a.health, "A's health should have decreased by 2.")
    self.assertEqual(4, b.health, "B's health should have decreased by 1.")


class RemoveDeadObjectsTest(unittest.TestCase):
  def testOneObjectDeadGetsRemoved(self):
    a = game.Ball('X')
    a.set_health(0)
    objects = [a]
    removed = game.RemoveDeadObjects(objects)
    self.assertEqual(set([a]), removed)
    self.assertEqual(0, len(objects), "Dead obj should have been removed.")

  def testOneObjectAliveStays(self):
    a = game.Ball('X')
    a.set_health(1)
    objects = [a]
    removed = game.RemoveDeadObjects(objects)
    self.assertEqual(set([]), removed)
    self.assertEqual([a], objects)

  def testTwoObjectsDeadThenAlive(self):
    a, b = game.Ball('A'), game.Ball('B')
    a.set_health(-1)
    b.set_health(5)
    objects = [a, b]
    removed = game.RemoveDeadObjects(objects)
    self.assertEqual(set([a]), removed)
    self.assertEqual([b], objects)

  def testTwoObjectsAliveThenDead(self):
    a, b = game.Ball('A'), game.Ball('B')
    a.set_health(-1)
    b.set_health(5)
    objects = [b, a]
    removed = game.RemoveDeadObjects(objects)
    self.assertEqual(set([a]), removed)
    self.assertEqual([b], objects)

  def testThreeObjectsAliveThenDeadTheAlive(self):
    a, b, c = game.Ball('A'), game.Ball('B'), game.Ball('C')
    a.set_health(5)
    b.set_health(-5)
    c.set_health(5)
    objects = [a, b, c]
    removed = game.RemoveDeadObjects(objects)
    self.assertEqual(set([b]), removed)
    self.assertEqual([a, c], objects)

  def testTwoConsecutiveDeadInARow(self):
    a, b, c = game.Ball('A'), game.Ball('B'), game.Ball('C')
    a.set_health(5)
    b.set_health(-5)
    c.set_health(-5)
    objects = [a, b, c]
    removed = game.RemoveDeadObjects(objects)
    self.assertEqual(set([b, c]), removed)
    self.assertEqual([a], objects)


class UpdatePlayerHealthTest(unittest.TestCase):
  def testShowsRightNumberOfHealthBars(self):
    player = game.Ball('*')
    player_health_max = 3
    player_health_obj = game.MakePlayerHealthObject(player_health_max)

    player.health = 0
    game.UpdatePlayerHealth(player, player_health_obj)
    self.assertEqual('   ', player_health_obj.strings[0])

    player.health = 1
    game.UpdatePlayerHealth(player, player_health_obj)
    self.assertEqual('X  ', player_health_obj.strings[0])

    player.health = 2
    game.UpdatePlayerHealth(player, player_health_obj)
    self.assertEqual('XX ', player_health_obj.strings[0])

    player.health = 3
    game.UpdatePlayerHealth(player, player_health_obj)
    self.assertEqual('XXX', player_health_obj.strings[0])


class MakeAndInstallPlayerHealthObjectTest(unittest.TestCase):
  def testInsertsIntoObjectsArray(self):
    objects = []
    player = None
    health_obj = game.MakeAndInstallPlayerHealthObject(player, objects, 5)
    self.assertEqual(2, len(objects))
    self.assertIn(health_obj, objects)

  def testRaisesErrorIfPlayerMaxHealthIsInvalid(self):
    with self.assertRaisesRegex(ValueError, "odd integer"):
      game.MakeAndInstallPlayerHealthObject(None, [], 4)
    with self.assertRaisesRegex(TypeError, "got: 5.0"):
      game.MakeAndInstallPlayerHealthObject(None, [], 5.0)

class MakeEnemiesTest(unittest.TestCase):
  def testMakesRightAmount(self):
    screen_width, screen_height = 50, 30
    enemies = game.MakeEnemies(10, screen_width, screen_height)
    # It's a bit hard to test details of the enemies since there is a random
    # choice being made. TODO: mock random.randint for more detailed checks.
    self.assertEqual(10, len(enemies))

class MoveTest(unittest.TestCase):
  def testMoveInboundsReturnsTrue(self):
    height, width = 20, 30
    obj = game.Ball('*')
    obj.set_position(width/2, height/2)
    obj.set_direction(1.0, 0.0)
    obj.set_speed(1)
    self.assertTrue(obj.move(height, width))

  def testMoveOutsideWithoutBounceStrategyReturnsFalse(self):
    height, width = 20, 30
    obj = game.Ball('*')
    # Place object at rightmost edge, and speeding to right so at next move
    # it leaves the boundaries
    obj.set_position(width-1, height/2)
    obj.set_speed(1)
    obj.set_direction(1.0, 0.0)
    obj.set_edge_strategy(game.EdgeStrategy.DISAPPEAR)
    self.assertFalse(obj.move(height, width))

  def testMoveOutsideWithBounceStrategyCausesBounce(self):
    height, width = 20, 30
    obj = game.Ball('*')
    # Place object at rightmost edge, and speeding to right so at next move
    # it leaves the boundaries
    obj.set_position(width-1, height/2)
    obj.set_speed(1)
    obj.set_direction(1.0, 0.0)
    obj.set_edge_strategy(game.EdgeStrategy.BOUNCE)
    self.assertGreater(obj.x_speed, 0, 'Should be moving right initially.')
    object_still_in_game = obj.move(height, width)
    self.assertTrue(object_still_in_game)
    self.assertLess(obj.x_speed, 0, 'Should be moving left after bouncing.')


if __name__ == '__main__':
  unittest.main()
