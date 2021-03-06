"""
Ainneve archetypes module.

This module encapsulates archetype-related data including character
trait definitions, and eventually default ability stats and OA talents to
select from when leveling up.

Archetype classes are meant to be loaded by name as needed to provide access
to archetype-specific data, not to be saved on a `Character` object. Only
the archetype name is stored in the character's `db` attribute handler,
and that value is generally set by the `apply_archetype` module function.

Module Functions:

    - `apply_archetype(char, name, reset=False)`

        Causes character `char` to become archetype `name`. Initializes db
        attributes on `char` to archetype defaults. Can be called twice on
        the same character with two different `name` parameters to create
        a dual archetype. May also be called with reset=True to remove
        any existing archetype and initialize the character with only the
        named one.

    - `get_remaining_allocation(traits)`

        Returns the nummber of trait points left for the player to allocate
        to primary traits.

    - `validate_primary_traits(traits)`

        Confirms that all primary traits total 30 points, and all but MAG
        are at least 1 and no greater than 10.

    - `calculate_secondary_traits(traits)`

        Called at the end of the character generation process to set initial
        values for secondary traits and save rolls.

    - `load_archetype(name)`

        Returns an instance of the named Archetype class.
"""

from world.rulebook import roll_max


class ArchetypeException(Exception):
    def __init__(self, msg):
        self.msg = msg


VALID_ARCHETYPES = ('Arcanist', 'Scout', 'Warrior')

PRIMARY_TRAITS = ('STR', 'PER', 'INT', 'DEX', 'CHA', 'VIT', 'MAG')
SECONDARY_TRAITS = ('HP', 'SP', 'BM', 'WM')
SAVE_ROLLS = ('FORT', 'REFL', 'WILL')
COMBAT_TRAITS = ('ATKM', 'ATKR', 'ATKU', 'DEF', 'PP')
OTHER_TRAITS = ('LV', 'XP', 'ENC', 'MV', 'ACT')

ALL_TRAITS = (PRIMARY_TRAITS + SECONDARY_TRAITS +
              SAVE_ROLLS + COMBAT_TRAITS + OTHER_TRAITS)

TOTAL_PRIMARY_POINTS = 30

def apply_archetype(char, name, reset=False):
    """Set a character's archetype and initialize traits.

    Used during character creation; initializes the traits collection. It
    can be called twice to make the character a Dual-Archetype.

    Args:
        char (Character): the character being initialized.
        name (str): single archetype name to apply. If the character already
            has a single archetype, it is combined with the existing as a
            dual archetype.
        reset (bool): if True, remove any current archetype and apply the
            named archetype as new.
    """
    name = name.capitalize()
    if name not in VALID_ARCHETYPES:
        raise ArchetypeException('Invalid archetype.')

    if char.db.archetype is not None:
        if not reset:
            if char.db.archetype == name:
                raise ArchetypeException('Character is already a {}'.format(name))

            name = '-'.join((char.db.archetype, name))

    archetype = load_archetype(name)
    char.db.traits = archetype.traits
    char.db.archetype = archetype.name


def get_remaining_allocation(traits):
    """Returns the number of trait points remaining to be assigned.

    Args:
        traits (TraitFactory): Partially loaded TraitFactory

    Returns:
        (int): number of trait points left for the player to allocate
    """
    allocated = sum(traits[t].base for t in PRIMARY_TRAITS)
    return TOTAL_PRIMARY_POINTS - allocated


def validate_primary_traits(traits):
    """Validates proposed primary trait allocations during chargen.

    Args:
        traits (TraitFactory): TraitFactory loaded with proposed final
            primary traits

    Returns:
        (tuple[bool, str]): first value is whether the traits are valid,
            second value is error message
    """
    total = sum(traits[t].base for t in PRIMARY_TRAITS)
    if total > TOTAL_PRIMARY_POINTS:
        return False, 'Too many trait points allocated.'
    if total < TOTAL_PRIMARY_POINTS:
        return False, 'Not enough trait points allocated.'
    else:
        return True, None


def calculate_secondary_traits(traits):
    """Calculates secondary traits

    Args:
        traits (TraitFactory): factory attribute with primary traits
        populated.
    """
    # secondary traits
    traits.HP.base = traits.VIT.actual
    traits.SP.base = traits.VIT.actual
    # save rolls
    traits.FORT.base = traits.VIT.actual
    traits.REFL.base = traits.DEX.actual
    traits.WILL.base = traits.INT.actual
    # combat
    traits.ATKM.base = traits.STR.actual
    traits.ATKR.base = traits.PER.actual
    traits.ATKU.base = traits.DEX.actual
    traits.DEF.base = traits.DEX.actual
    # mana
    traits.BM.max = 10 if traits.MAG.base > 0 else 0
    traits.WM.max = 10 if traits.MAG.base > 0 else 0
    # misc
    traits.STR.carry_factor = 10
    traits.STR.lift_factor = 20
    traits.STR.push_factor = 40
    traits.ENC.max = traits.STR.lift_factor * traits.STR.actual


def load_archetype(name):
    """Loads an instance of the named Archetype class.

    Args:
        name (str): Name of either single or dual-archetype

    Return:
        (Archetype): An instance of the requested archetype class.
    """
    name = name.title()
    if '-' in name:  # dual arch
        archetype = _make_dual(*[load_archetype(n) for
                                 n in name.split('-', 1)])
    else:
        try:
            archetype = globals().get(name, None)()
        except TypeError:
            raise ArchetypeException("Invalid archetype specified.")
    return archetype

def _make_dual(a, b):
    """Creates a dual archetype class out of two basic `Archetype` classes.

    Args:
        a (Archetype): first component Archetype
        b (Archetype): second component Archetype

    Returns:
        (Archetype): dual Archetype class
    """
    if '-' in a.name or '-' in b.name:
        raise ArchetypeException('Cannot create Triple-Archetype')
    if a.name == b.name:
        raise ArchetypeException('Cannot create dual of the same Archetype')

    names = {
        frozenset(['Warrior', 'Scout']): 'Warrior-Scout',
        frozenset(['Warrior', 'Arcanist']): 'Warrior-Arcanist',
        frozenset(['Scout', 'Arcanist']): 'Arcanist-Scout'
    }
    dual = Archetype()
    for key, trait in dual.traits.iteritems():
        trait['base'] = (a.traits.get(key, trait)['base'] +
                         b.traits.get(key, trait)['base']) // 2
        trait['mod'] = (a.traits.get(key, trait)['mod'] +
                        b.traits.get(key, trait)['mod']) // 2
    dual.health_roll = min(a.health_roll, b.health_roll, key=roll_max)
    dual.name = names[frozenset([a.name, b.name])]
    dual.__class__.__name__ = dual.name.replace('-', '')
    return dual


# Archetype Classes


class Archetype(object):
    """Base archetype class containing default values for all traits."""
    def __init__(self):
        self.name = None

        # base traits data
        self.traits = {
            # primary
            'STR': {'type': 'trait', 'base': 1, 'mod': 0, 'name': 'Strength'},
            'PER': {'type': 'trait', 'base': 1, 'mod': 0, 'name': 'Perception'},
            'INT': {'type': 'trait', 'base': 1, 'mod': 0, 'name': 'Intelligence'},
            'DEX': {'type': 'trait', 'base': 1, 'mod': 0, 'name': 'Dexterity'},
            'CHA': {'type': 'trait', 'base': 1, 'mod': 0, 'name': 'Charisma'},
            'VIT': {'type': 'trait', 'base': 1, 'mod': 0, 'name': 'Vitality'},
            # magic
            'MAG': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Magic'},
            'BM': {'type': 'gauge', 'base': 0, 'mod': 0, 'min': 0, 'max': 0, 'name': 'Black Mana'},
            'WM': {'type': 'gauge', 'base': 0, 'mod': 0, 'min': 0, 'max': 0, 'name': 'White Mana'},
            # secondary
            'HP': {'type': 'gauge', 'base': 0, 'mod': 0, 'name': 'Health'},
            'SP': {'type': 'gauge', 'base': 0, 'mod': 0, 'name': 'Stamina'},
            # saves
            'FORT': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Fortitude Save'},
            'REFL': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Reflex Save'},
            'WILL': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Will Save'},
            # combat
            'ATKM': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Melee Attack'},
            'ATKR': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Ranged Attack'},
            'ATKU': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Unarmed Attack'},
            'DEF': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Defense'},
            'ACT': {'type': 'counter', 'base': 0, 'mod': 0, 'min': 0, 'name': 'Action Points'},
            'PP': {'type': 'counter', 'base': 0, 'mod': 0, 'min': 0, 'name': 'Power Points'},
            # misc
            'ENC': {'type': 'counter', 'base': 0, 'mod': 0, 'min': 0, 'name': 'Carry Weight'},
            'MV': {'type': 'trait', 'base': 6, 'mod': 0, 'name': 'Movement Points'},
            'LV': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Level'},
            'XP': {'type': 'trait', 'base': 0, 'mod': 0, 'name': 'Experience',
                   'extra': {'level_boundaries': (500, 2000, 4500, 'unlimited')}},
        }
        self.health_roll = None


class Arcanist(Archetype):
    """Represents the Arcanist archetype."""
    def __init__(self):
        super(Arcanist, self).__init__()
        self.name = 'Arcanist'

        # set starting trait values
        self.traits['PER']['base'] = 4
        self.traits['INT']['base'] = 6
        self.traits['CHA']['base'] = 4
        self.traits['MAG']['base'] = 6
        self.traits['SP']['mod'] = -2
        self.traits['MV']['base'] = 7

        self.health_roll = '1d6-1'


class Scout(Archetype):
    """Represents the Scout archetype."""
    def __init__(self):
        super(Scout, self).__init__()
        self.name = 'Scout'

        # set starting trait values
        self.traits['STR']['base'] = 4
        self.traits['PER']['base'] = 6
        self.traits['INT']['base'] = 6
        self.traits['DEX']['base'] = 4

        self.health_roll = '1d6'


class Warrior(Archetype):
    """Represents the Warrior archetype."""
    def __init__(self):
        super(Warrior, self).__init__()
        self.name = 'Warrior'

        # set starting trait values
        self.traits['STR']['base'] = 6
        self.traits['DEX']['base'] = 4
        self.traits['CHA']['base'] = 4
        self.traits['VIT']['base'] = 6
        self.traits['PP']['base'] = 2
        self.traits['MV']['base'] = 5

        self.health_roll = '1d6+1'
