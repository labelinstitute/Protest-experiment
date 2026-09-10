from otree.api import *
import math
import json
import os
import csv


doc = """
Protest game:
- citizen-only app
- 8 rounds
- 4 rounds per leader
- CSV network loading
- live neighbor color updates
- leaders do not appear in this app
"""


class C(BaseConstants):
    NAME_IN_URL = 'protest'
    PLAYERS_PER_GROUP = 14
    NUM_ROUNDS = 8

    SELFISH_LEADER_LOSS = 20
    LESS_SELFISH_LEADER_LOSS = 11

    ALLOCATIONS = {
        'A': {'leader': 30, 'gold': 12, 'silver': 10, 'bronze': 8},
        'B': {'leader': 21, 'gold': 15, 'silver': 13, 'bronze': 11},
    }

    FAILED_PROTEST_PENALTY = {
        'gold': 6,
        'silver': 6,
        'bronze': 4,
    }

    SUCCESS_BONUS = {
        'A': {'gold': 3, 'silver': 4, 'bronze': 5},
        'B': {'gold': 0, 'silver': 1, 'bronze': 2},
    }

    ASSIGNMENTS_CSV = 'assignments.csv'


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    total_protesters = models.IntegerField(initial=0)
    protest_success = models.BooleanField(initial=False)

    active_leader_id = models.IntegerField(blank=True, null=True)
    active_leader_choice = models.StringField(blank=True)

    live_choices_json = models.LongStringField(blank=True, initial='')


class Player(BasePlayer):
    protest = models.StringField(
        choices=['protest', 'undecided', 'no_protest'],
        blank=True
    )

    final_payoff = models.IntegerField(initial=0)


# ------------------------------------------------
# ROLE HELPERS
# ------------------------------------------------

def is_leader(player: Player):
    return player.participant.vars.get('final_role') == 'leader'


def is_citizen(player: Player):
    return player.participant.vars.get('final_role') == 'citizen'


# ------------------------------------------------
# NETWORK LOADING
# ------------------------------------------------

_ASSIGNMENTS = None


def parse_neighbors(s: str):
    return [
        int(x.strip().strip('"').strip("'"))
        for x in (s or "").split(",")
        if x.strip()
    ]


def load_round_assignments():
    global _ASSIGNMENTS
    if _ASSIGNMENTS is not None:
        return _ASSIGNMENTS

    path = os.path.join(os.path.dirname(__file__), C.ASSIGNMENTS_CSV)
    assignments = {}

    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            round_number = int(row["round"])
            node_id = int(row["node_id"])

            assignments.setdefault(round_number, {})[node_id] = dict(
                neighbors=parse_neighbors(row["neighbors_list"]),
                x=float(row["position_x"]),
                y=float(row["position_y"]),
            )

    _ASSIGNMENTS = assignments
    return _ASSIGNMENTS


def ensure_network_assigned(group: Group):
    round_number = group.round_number
    key = f'network_assigned_{group.id_in_subsession}_round_{round_number}'

    if group.session.vars.get(key):
        return

    citizens = sorted(
        [p for p in group.get_players() if is_citizen(p)],
        key=lambda p: p.participant.vars.get('rank_position', 999999)
    )

    assignments_by_round = load_round_assignments()
    if round_number not in assignments_by_round:
        raise Exception(f'No CSV assignments found for round {round_number}')

    assignments = assignments_by_round[round_number]

    if len(citizens) != len(assignments):
        raise Exception(
            f'Mismatch between CSV nodes ({len(assignments)}) and citizens ({len(citizens)}) in round {round_number}'
        )

    for idx, p in enumerate(citizens, start=1):
        node_data = assignments[idx]
        p.participant.vars['node_id'] = idx
        p.participant.vars['neighbors'] = node_data['neighbors']
        p.participant.vars['position'] = dict(
            x=node_data['x'],
            y=node_data['y'],
        )

    group.session.vars[key] = True


def ensure_live_choices_initialized(group: Group):
    if group.field_maybe_none('live_choices_json'):
        return json.loads(group.live_choices_json)

    choices = {}
    for p in group.get_players():
        if is_citizen(p):
            node_id = str(p.participant.vars.get('node_id'))
            current_choice = p.field_maybe_none('protest')

            if current_choice in ['protest', 'undecided', 'no_protest']:
                choices[node_id] = current_choice
            else:
                choices[node_id] = 'undecided'

    group.live_choices_json = json.dumps(choices)
    return choices


# ------------------------------------------------
# ACTIVE LEADER / CHOICE
# ------------------------------------------------

def get_active_leader(group: Group, round_number):
    ref_player = group.get_players()[0]
    leader1_id = ref_player.participant.vars.get('leader1_id')
    leader2_id = ref_player.participant.vars.get('leader2_id')
    return leader1_id if round_number <= 4 else leader2_id


def get_active_choice(group: Group, round_number):
    ref_player = group.get_players()[0]
    leader1_choice = ref_player.participant.vars.get('leader1_choice')
    leader2_choice = ref_player.participant.vars.get('leader2_choice')
    return leader1_choice if round_number <= 4 else leader2_choice


def get_success_threshold(group: Group):
    return 9


# ------------------------------------------------
# PAYOFF HELPERS
# ------------------------------------------------

def role_icon(tier):
    if tier == 'gold':
        return 'role_icons/gold.jpg'
    if tier == 'silver':
        return 'role_icons/silver.jpg'
    return 'role_icons/bronze.jpg'


def leader_loss_for_choice(leader_choice):
    if leader_choice == 'A':
        return C.SELFISH_LEADER_LOSS
    elif leader_choice == 'B':
        return C.LESS_SELFISH_LEADER_LOSS
    return 0


def success_bonus_for_player(leader_choice, tier):
    return C.SUCCESS_BONUS.get(leader_choice, {}).get(tier, 0)


def failed_protest_penalty_for_player(tier):
    return C.FAILED_PROTEST_PENALTY.get(tier, 0)


# ------------------------------------------------
# LIVE METHODS
# ------------------------------------------------

def build_payload(group: Group):
    choices = ensure_live_choices_initialized(group)
    return dict(live_choices=choices)


def live_choice(player: Player, data):
    group = player.group
    ensure_network_assigned(group)
    choices = ensure_live_choices_initialized(group)

    action = data.get('action')
    node_id = str(player.participant.vars.get('node_id'))

    if action in ['protest', 'undecided', 'no_protest']:
        player.protest = action
        choices[node_id] = action
    elif action in ['ping', None]:
        pass
    else:
        return {0: build_payload(group)}

    group.live_choices_json = json.dumps(choices)
    return {0: build_payload(group)}


# ------------------------------------------------
# PAGES
# ------------------------------------------------

class CitizenDecision(Page):
    form_model = 'player'
    form_fields = ['protest']

    @staticmethod
    def is_displayed(player: Player):
        return is_citizen(player)

    @staticmethod
    def live_method(player: Player, data):
        return live_choice(player, data)

    @staticmethod
    def get_timeout_seconds(player: Player):
        return 20

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        ensure_network_assigned(group)
        live_choices = ensure_live_choices_initialized(group)

        leader_choice = get_active_choice(group, player.round_number)
        
        if leader_choice not in C.ALLOCATIONS:
            raise Exception(
                f"Missing or invalid leader choice in round {player.round_number}. "
                f"leader_choice={leader_choice}"
            )
        leader_payoff = C.ALLOCATIONS[leader_choice]['leader']
        leader_loss = leader_loss_for_choice(leader_choice)

        leader_choice_text = (
            f"Le leader a choisi {leader_choice} : il conservera {leader_payoff} si la protestation échoue " 
            f"et perdra {leader_loss} si elle réussit."
        )
        

        tier = player.participant.vars.get('citizen_tier')
        if not tier:
            raise Exception(
                f"Missing citizen_tier for player {player.id_in_group}. "
                f"final_role={player.participant.vars.get('final_role')}, "
                f"rank_position={player.participant.vars.get('rank_position')}"
            )

        if tier not in ['gold', 'silver', 'bronze']:
            raise Exception(
                f"Invalid citizen_tier '{tier}' for player {player.id_in_group}"
            )

        tier_label = tier.capitalize()

        base = C.ALLOCATIONS[leader_choice][tier]
        success_bonus = success_bonus_for_player(leader_choice, tier)
        fail_penalty = failed_protest_penalty_for_player(tier)

        success_payoff = base + success_bonus
        fail_undecided_payoff = base
        fail_protest_payoff = base - fail_penalty

        return dict(
            leader_choice=leader_choice,
            leader_choice_text=leader_choice_text,
            round_number=player.round_number,
            tier=tier,
            tier_label=tier_label,
            base_payoff=base,
            success_payoff=success_payoff,
            fail_undecided_payoff=fail_undecided_payoff,
            fail_protest_payoff=fail_protest_payoff,
            success_bonus_display=success_bonus,
            failure_penalty_display=fail_penalty,
            role_icon_path=role_icon(tier),
            timeout_seconds=20,
            node_id=player.participant.vars.get('node_id'),
            neighbors_json=json.dumps(player.participant.vars.get('neighbors', [])),
            live_choices_json=json.dumps(live_choices),
        )

    @staticmethod
    def error_message(player: Player, values):
        if values.get('protest') in [None, '']:
            return 'Please choose.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.field_maybe_none('protest') is None:
            player.protest = 'undecided'

        choices = ensure_live_choices_initialized(player.group)
        node_id = str(player.participant.vars.get('node_id'))
        choices[node_id] = player.protest
        player.group.live_choices_json = json.dumps(choices)


class CitizenResultsWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return is_citizen(player)

    after_all_players_arrive = 'compute_outcome'


def compute_outcome(group: Group):
    players = group.get_players()

    group.active_leader_id = get_active_leader(group, group.round_number)
    group.active_leader_choice = get_active_choice(group, group.round_number)

    leader_choice = group.active_leader_choice
    if leader_choice not in C.ALLOCATIONS:
        raise Exception(
            f"Missing or invalid leader choice in compute_outcome, round {group.round_number}. "
            f"leader_choice={leader_choice}"
        )

    citizens = [p for p in players if is_citizen(p)]
    total_protesters = sum(1 for p in citizens if p.field_maybe_none('protest') == 'protest')

    group.total_protesters = total_protesters
    group.protest_success = total_protesters >= get_success_threshold(group)

    for p in players:
        if is_leader(p):
            base = C.ALLOCATIONS[leader_choice]['leader']
            loss = leader_loss_for_choice(leader_choice)
            p.final_payoff = base - loss if group.protest_success else base

        elif is_citizen(p):
            tier = p.participant.vars.get('citizen_tier')

            if not tier:
                raise Exception(
                    f"Missing citizen_tier in compute_outcome for player {p.id_in_group}. "
                    f"final_role={p.participant.vars.get('final_role')}, "
                    f"rank_position={p.participant.vars.get('rank_position')}"
                )

            if tier not in ['gold', 'silver', 'bronze']:
                raise Exception(
                    f"Invalid citizen_tier '{tier}' in compute_outcome for player {p.id_in_group}"
                )

            base = C.ALLOCATIONS[leader_choice][tier]

            if group.protest_success:
                bonus = success_bonus_for_player(leader_choice, tier)
                p.final_payoff = base + bonus
            else:
                penalty = failed_protest_penalty_for_player(tier)
                p.final_payoff = base - penalty if p.protest == 'protest' else base

        else:
            raise Exception(
                f"Player {p.id_in_group} has invalid final_role={p.participant.vars.get('final_role')}"
            )

        summary_row = dict(
            round_number=group.round_number,
            leader_choice=group.active_leader_choice,
            protest_success=group.protest_success,
            total_protesters=group.total_protesters,
            payoff=p.final_payoff,
        )

        if 'protest_summary' not in p.participant.vars:
            p.participant.vars['protest_summary'] = []

        p.participant.vars['protest_summary'].append(summary_row)


class CitizenResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return is_citizen(player)

    @staticmethod
    def vars_for_template(player: Player):
        leader_choice = player.group.active_leader_choice
        tier = player.participant.vars.get('citizen_tier')
        tier_label = tier.capitalize() if tier else ''
        protest_choice = player.field_maybe_none('protest') or 'undecided'

        base_payoff = C.ALLOCATIONS[leader_choice][tier]

        if player.group.protest_success:
            change_amount = success_bonus_for_player(leader_choice, tier)
            operator = '+'
            final_payoff = base_payoff + change_amount
            explanation_text = 'The protest succeeded, so your payoff increased.'
        else:
            if protest_choice == 'protest':
                change_amount = failed_protest_penalty_for_player(tier)
                operator = '-'
                final_payoff = base_payoff - change_amount
                explanation_text = 'The protest failed, and because you protested, your payoff decreased.'
            else:
                change_amount = 0
                operator = '+'
                final_payoff = base_payoff
                explanation_text = 'The protest failed, but because you did not protest, your payoff stayed the same.'

        return dict(
            protest_success=player.group.protest_success,
            total_protesters=player.group.total_protesters,
            payoff=player.final_payoff,
            round_number=player.round_number,
            tier=tier,
            tier_label=tier_label,
            protest_choice=protest_choice,
            base_payoff=base_payoff,
            change_amount=change_amount,
            operator=operator,
            final_payoff=final_payoff,
            explanation_text=explanation_text,
        )


class NextRound(Page):
    @staticmethod
    def is_displayed(player: Player):
        return is_citizen(player)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            round_number=player.round_number,
            total_rounds=C.NUM_ROUNDS,
            switch_leader=player.round_number == 4,
        )

page_sequence = [CitizenDecision, CitizenResultsWaitPage, NextRound]