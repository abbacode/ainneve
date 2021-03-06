"""
Command test module
"""
from evennia.utils.test_resources import EvenniaTest
from evennia.commands.default.tests import CommandTest
from commands.equip import *
from commands.chartraits import CmdSheet, CmdTraits
from typeclasses.characters import Character
from typeclasses.weapons import Weapon
from world.races import apply_race
from world.archetypes import apply_archetype, calculate_secondary_traits


class ItemEncumbranceTestCase(EvenniaTest):
    """Test case for at_get/at_drop hooks."""
    character_typeclass = Character
    object_typeclass = Weapon

    def setUp(self):
        super(ItemEncumbranceTestCase, self).setUp()
        apply_archetype(self.char1, 'warrior')
        apply_race(self.char1, 'human', 'cunning')
        self.char1.traits.STR.base += 3
        self.char1.traits.VIT.base += 3
        self.char1.traits.DEX.base += 2
        calculate_secondary_traits(self.char1.traits)
        self.obj1.db.desc = 'Test Obj'
        self.obj1.db.damage = 1
        self.obj1.db.weight = 1.0
        self.obj2.swap_typeclass('typeclasses.armors.Armor',
                                 clean_attributes=True,
                                 run_start_hooks=True)
        self.obj2.db.toughness = 1
        self.obj2.db.weight = 18.0

    def test_get_item(self):
        """test that item get hook properly affects encumbrance"""
        self.assertEqual(self.char1.traits.ENC.actual, 0)
        self.assertEqual(self.char1.traits.MV.actual, 5)
        self.char1.execute_cmd('get Obj')
        self.assertEqual(self.char1.traits.ENC.actual, 1.0)
        self.assertEqual(self.char1.traits.MV.actual, 5)
        # Obj2 is heavy enough to incur a movement penalty
        self.char1.execute_cmd('get Obj2')
        self.assertEqual(self.char1.traits.ENC.actual, 19.0)
        self.assertEqual(self.char1.traits.MV.actual, 4)

    def test_drop_item(self):
        """test that item drop hook properly affects encumbrance"""
        self.char1.execute_cmd('get Obj')
        self.char1.execute_cmd('get Obj2')
        self.assertEqual(self.char1.traits.ENC.actual, 19.0)
        self.assertEqual(self.char1.traits.MV.actual, 4)
        self.char1.execute_cmd('drop Obj2')
        self.assertEqual(self.char1.traits.ENC.actual, 1.0)
        self.assertEqual(self.char1.traits.MV.actual, 5)


class EquipTestCase(CommandTest):
    """Test case for EquipHandler and commands."""
    character_typeclass = Character
    object_typeclass = Weapon

    def setUp(self):
        super(EquipTestCase, self).setUp()
        apply_archetype(self.char1, 'warrior')
        apply_race(self.char1, 'human', 'cunning')
        self.obj1.db.desc = 'Test Obj'
        self.obj1.db.damage = 1
        self.obj1.db.weight = 1.0
        self.obj2.db.desc = 'Test Obj2'
        self.obj2.swap_typeclass('typeclasses.armors.Armor',
                                 clean_attributes=True,
                                 run_start_hooks=True)
        self.obj2.db.toughness = 1
        self.obj2.db.weight = 2.0

    def test_wield(self):
        """test wield command"""
        # can't wield from the ground
        self.call(CmdWield(), 'Obj', "You don't have Obj in your inventory.")
        # pick it up to wield a weapon
        self.char1.execute_cmd('get Obj')
        self.call(CmdWield(), 'Obj', "You wield Obj.")
        # can't wield armor
        self.char1.execute_cmd('get Obj2')
        self.call(CmdWield(), 'Obj2', "You can't wield Obj2.")

    def test_wear(self):
        """test wear command"""
        # can't wear from the ground
        self.call(CmdWear(), 'Obj2', "You don't have Obj2 in your inventory.")
        # pick it up to wield a weapon
        self.char1.execute_cmd('get Obj2')
        self.call(CmdWear(), 'Obj2', "You wear Obj2.")
        # wear does wield a weapon
        self.char1.execute_cmd('get Obj')
        self.call(CmdWear(), 'Obj', "You can't wear Obj.")

    def test_equip_list(self):
        """test the equip command"""
        self.call(CmdEquip(), "", "You have nothing in your equipment.")
        self.char1.execute_cmd('get Obj')
        self.char1.execute_cmd('wield Obj')
        self.char1.execute_cmd('get Obj2')
        self.char1.execute_cmd('wear Obj2')
        output = (
"YYour equipment:n\n"
"   Wield1: Obj                  (Damage:  1)     \n"
"    Armor: Obj2                 (Toughness:  1)")
        self.call(CmdEquip(), "", output)
        self.char1.execute_cmd('drop Obj')
        self.call(CmdEquip(), "", "YYour equipment:n\n    Armor: Obj2")

    def test_equip_item(self):
        """test equipping items with equip"""
        self.char1.execute_cmd('get Obj')
        self.char1.execute_cmd('get Obj2')
        self.call(CmdEquip(), "Obj", "You wield Obj.")
        self.call(CmdEquip(), "Obj2", "You wear Obj2.")

    def test_remove(self):
        """test the remove command"""
        self.call(CmdRemove(), "Obj", "You do not have Obj equipped.")
        self.char1.execute_cmd('get Obj')
        self.char1.execute_cmd('wield Obj')
        self.call(CmdRemove(), "Obj", "You remove Obj.")

    def test_inventory(self):
        """test the inventory command"""
        # empty inventory
        self.call(CmdInventory(), "", "You are not carrying anything.")
        # can see an object when picked up
        self.char1.execute_cmd('get Obj')
        self.call(CmdInventory(), "", "YYou are carrying:n\n Obj  Test Obj")
        # but not when equipped
        self.char1.execute_cmd('wield Obj')
        self.call(CmdInventory(), "", "You are not carrying anything.")


class CharTraitsTestCase(CommandTest):
    """Character sheet and traits test case."""
    def setUp(self):
        self.character_typeclass = Character
        super(CharTraitsTestCase, self).setUp()
        apply_archetype(self.char1, 'warrior')
        self.char1.traits.STR.base += 3
        self.char1.traits.PER.base += 1
        self.char1.traits.DEX.base += 1
        self.char1.traits.VIT.base += 3
        calculate_secondary_traits(self.char1.traits)

    def test_sheet(self):
        """test character sheet display"""
        sheet_output = (
"==============[ Character Info ]===============\n" + (77 * " ") + "\n"
"  Name:                         Char     XP:     0 /       500   Level:   0  \n"
"  Archetype:                 Warrior                                         \n"
+ (39 * " ") + "\n"
"     HP      SP      BM      WM      Primary Traits   Strength    :   9  \n"
"  ~~~~~~~~+~~~~~~~~+~~~~~~~~+~~~~~~~~   ~~~~~~~~~~~~~~   Perception  :   2  \n"
"    9 / 9   9 / 9   0 / 0   0 / 0                     Intelligence:   1  \n"
"                                                         Dexterity   :   5  \n"
"  Race:                         None                     Charisma    :   4  \n"
"  Focus:                        None                     Vitality    :   9  \n"
"  Description                                            Magic       :   0  \n"
"  ~~~~~~~~~~~                          \n"
"  None                                  Save Rolls       Fortitude   :   9  \n"
"                                        ~~~~~~~~~~       Reflex      :   5  \n"
"                                                         Will        :   1  \n"
"  Encumbrance                          \n"
"  ~~~~~~~~~~~                           Combat Stats     Melee       :   9  \n"
"  Carry Weight:             0 /  180    ~~~~~~~~~~~~     Ranged      :   2  \n"
"  Encumbrance Penalty:             0    Power Point      Unarmed     :   5  \n"
"  Movement Points:                 5    Bonus:    +2     Defense     :   5")
        self.call(CmdSheet(), "", sheet_output)

    def test_traits(self):
        """test traits command"""
        # test no args
        self.call(CmdTraits(), "", "Usage: traits <traitgroup>")
        # test primary traits
        output = (
"YPrimary Traitsn|\n"
" Strength         :   9  Perception       :   2  Intelligence     :   1 \n"
" Dexterity        :   5  Charisma         :   4  Vitality         :   9 \n"
" Magic            :   0")
        self.call(CmdTraits(), "pri", output)
        # test secondary traits
        output = (
"YSecondary Traitsn|\n"
" Health                        :   9  Black Mana                   :   0 \n"
" Stamina                       :   9  White Mana                   :   0")
        self.call(CmdTraits(), "secondary", output)
        # test save rolls
        output = (
"YSave Rollsn|\n"
" Fortitude Save   :   9  Reflex Save      :   5  Will Save        :   1")
        self.call(CmdTraits(), "sav", output)
        # test combat stats
        output = (
"YCombat Statsn|\n"
" Melee Attack     :   9  Ranged Attack    :   2  Unarmed Attack   :   5 \n"
" Defense          :   5  Power Points     :   2")
        self.call(CmdTraits(), "com", output)
