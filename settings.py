from os import environ

DEBUG = False

SESSION_CONFIGS = [
    dict(
        name='protest',
        display_name='Protest Experiment',
        num_demo_participants=14, #for testing it atao 6
        app_sequence=[
        'intro',
        'initial_preference',
        'tournament',
        'role_assignment',
        'leader_decision',
        'protest',
        'leader_survey',
        'results',  # protest payoff computed here

        # ===== EXTRA TASKS =====
        'TOM',
        'digit_span',
        'corsi',
        'ravens_task',

        # ===== NON-PAYING SURVEYS =====
        'demo',
        'bft10',


        # ===== FINAL PAYMENT =====
        'final_payment',
],
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    #real_world_currency_per_point=1/12,  # $1 per 15 points
    real_world_currency_per_point=0,   # no cash conversion
    participation_fee=0,              # show-up fee
    doc="",
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

LANGUAGE_CODE = 'fr'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = ""

SECRET_KEY = '8675309jennyidontknow'  # Change this to any random string

ROOMS = [
    {
        'name': 'econ_lab',
        'display_name': 'Econ Lab 1',
    },
    {
        'name': 'econ_lab2',
        'display_name': 'Econ Lab 2',
    },
    {
        'name': 'econ_lab3',
        'display_name': 'Econ Lab 3',
    },
    {
        'name': 'econ_lab4',
        'display_name': 'Econ Lab 4',
    },
]

'''ROOMS = [
    {
        'name': 'econ_lab',
        'display_name': 'Econ Lab 1',
        'participant_label_file': '_rooms/econ_lab.txt',
    },
    {
        'name': 'econ_lab2',
        'display_name': 'Econ Lab 2',
        'participant_label_file': '_rooms/econ_lab2.txt',
    },
    {
        'name': 'econ_lab3',
        'display_name': 'Econ Lab 3',
        'participant_label_file': '_rooms/econ_lab3.txt',
    },
    {
        'name': 'econ_lab4',
        'display_name': 'Econ Lab 4',
        'participant_label_file': '_rooms/econ_lab4.txt',
    },
]'''
INSTALLED_APPS = ['otree']

