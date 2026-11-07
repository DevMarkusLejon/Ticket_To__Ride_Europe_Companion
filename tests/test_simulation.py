from collections import Counter
from random import Random

import pytest

from ttr_europe.game_state import GameState
from ttr_europe.models import Route, RouteColor
from ttr_europe.simulation import COLORS, LOCO, Game, Score, Ticket, TrainDeck, load_europe, longest_trail, scores
from ttr_europe.strategies import Bot, Policy
from ttr_europe.tournament import play, tournament


@pytest.fixture
def game():
    return Game(*load_europe(), seats=4, seed=42)


def test_classic_board_and_tickets():
    board, tickets = load_europe()
    assert Counter(r.length for r in board.routes.values()) == {1: 4, 2: 35, 3: 30, 4: 29, 6: 2, 8: 1}
    assert Counter(r.color.value for r in board.routes.values()) == {**dict.fromkeys(COLORS, 8), "gray": 37}
    assert sum(r.is_tunnel for r in board.routes.values()) == 18
    assert sum(r.has_ferry for r in board.routes.values()) == 13
    assert board.routes["palermo_smyrna"].ferry_locomotives_required == 2
    assert board.routes["petrograd_stockholm"].is_tunnel
    groups = Counter(r.parallel_group for r in board.routes.values() if r.parallel_group)
    assert len(groups) == 11 and set(groups.values()) == {2}
    assert Counter(t.type for t in tickets) == {"regular": 40, "long": 6}
    assert len({frozenset((t.source_city, t.target_city)) for t in tickets}) == 46
    assert all(city in board.cities for t in tickets for city in (t.source_city, t.target_city))
    assert next(t.points for t in tickets if t.source_city == "stockholm") == 11


def test_opening_and_later_ticket_discards(game):
    p = game.players[0]
    for offer in game.opening_offers:
        assert Counter(t.type for t in offer) == {"long": 1, "regular": 3}
    assert len(game.tickets) == 28
    assert all(p.hand.total() == 4 and p.trains == 45 for p in game.players)
    offer = game.opening_offers[0]
    with pytest.raises(ValueError):
        game.keep_tickets(p, offer, offer[:1], opening=True)
    game.keep_tickets(p, offer, offer[1:3], opening=True)
    assert all(t not in game.tickets for t in offer)
    game.tickets = game.tickets[-2:]
    drawn = game.draw_tickets()
    assert len(drawn) == 2 and not game.tickets
    game.keep_tickets(p, drawn, drawn[:1], opening=False)
    assert game.tickets == drawn[1:]


def test_face_up_and_blind_locomotives():
    deck = TrainDeck(Random(7))
    deck.market = ["red", LOCO, "green", "pink", "white"]
    deck.pile = ["orange", LOCO, "yellow", "blue"]
    hand = Counter()
    assert deck.draw(hand, [LOCO]) and hand == {LOCO: 1}
    assert deck.draw(hand, ["red", LOCO]) and hand == {LOCO: 2, "red": 1}
    # The second locomotive came from the top of the pile. The replaced red exposed yellow.
    deck.market = [LOCO, "red", "blue", "yellow", "pink"]
    deck.pile = []
    deck.discard = []
    hand.clear()
    deck.draw(hand, ["red", LOCO])
    assert hand == {"red": 1, "blue": 1}


def test_market_refresh_and_deck_exhaustion():
    deck = TrainDeck(Random(5))
    deck.market = [LOCO] * 3 + ["green", "yellow"]
    deck.pile = ["red"] * 5
    deck.fill_market()
    assert deck.market == ["red"] * 5
    assert Counter(deck.take(5)) == {LOCO: 3, "green": 1, "yellow": 1}
    assert not deck.take(1)
    deck.market = [LOCO] * 5
    deck.fill_market()
    assert not deck.market
    hand = Counter()
    assert deck.draw(hand, []) and hand == {LOCO: 2}


@pytest.mark.parametrize("seats", [2, 3, 4, 5])
def test_double_routes(game, seats):
    state = GameState(game.state.board, player_count=seats)
    state.claim_route("madrid_pamplona", "a")
    assert state.is_available("madrid_pamplona", "a")
    assert not state.is_claimable("madrid_pamplona_2", "a")
    assert state.is_claimable("madrid_pamplona_2", "b") == (seats >= 4)
    with pytest.raises(ValueError):
        state.claim_route("madrid_pamplona_2", "a")


def test_ferry_payments_require_wilds_and_one_color(game):
    p = game.players[0]
    r = game.state.board.routes["palermo_smyrna"]
    p.hand = Counter(red=6, blue=2, locomotive=2)
    for invalid in (["red"] * 6, ["red", "red", "blue", "blue", LOCO, LOCO]):
        with pytest.raises(ValueError):
            game.claim(p, r, invalid)
    assert game.claim(p, r)
    assert p.hand == Counter(red=2, blue=2) and p.trains == 39


@pytest.mark.parametrize(("hand", "reveal", "limit", "success", "left"), [
    ({"black": 3}, ["black"], 3, False, {"black": 3}),
    ({"black": 3, LOCO: 1}, ["black"], 3, True, {}),
    ({"black": 4}, [LOCO], 0, False, {"black": 4}),
    ({LOCO: 3}, ["black", "red"], 3, True, {}),
    ({LOCO: 3, "red": 2}, [LOCO], 3, False, {LOCO: 3, "red": 2}),
    ({"black": 3}, [], 3, True, {}),
])
def test_tunnels(game, hand, reveal, limit, success, left):
    p = game.players[0]
    p.hand = Counter(hand)
    game.deck.pile = list(reveal)
    game.deck.discard = []
    r = game.state.board.routes["madrid_pamplona"]
    assert game.claim(p, r, max_tunnel_extra=limit) == success
    assert p.trains == (42 if success else 45) and p.hand == Counter(left)
    assert (r.route_id in game.state.route_owner) == success
    assert len(game.deck.discard) == len(reveal) + (sum(hand.values()) - sum(left.values()))


def test_stations_share_one_choice_across_tickets_and_do_not_extend_express(game):
    p, opponent = game.players[:2]
    p.hand = Counter(red=3, blue=2, locomotive=1)
    p.tickets = [Ticket("dieppe", "brest", 7, "regular"), Ticket("dieppe", "paris", 8, "regular")]
    for rid in ("dieppe_brest", "paris_dieppe"):
        r = game.state.board.routes[rid]
        opponent.hand = Counter({r.color.value: r.length})
        game.claim(opponent, r)
    game.station(p, "dieppe")
    assert scores(game)[0] == Score(8 - 7 + 8, 1, 2, False)
    assert scores(game)[1].express
    with pytest.raises(ValueError):
        game.station(opponent, "dieppe")
    game.station(p, "brest")
    assert p.hand.total() == 3 and scores(game)[0].points == 19
    game.station(p, "roma")
    assert p.hand.total() == 0
    with pytest.raises(ValueError):
        game.station(p, "paris")


def test_longest_trail_includes_cycles_but_never_reuses_a_track():
    def route(a, b, n):
        return Route(a+b, a, b, n, RouteColor.GRAY)
    assert longest_trail([route("a", "b", 2), route("b", "c", 3), route("c", "a", 1),
                          route("a", "d", 4), route("x", "y", 8)]) == 10
    assert longest_trail([route("a", b, 1) for b in "bcde"]) == 2
    assert Score(80, 3, 1, False).rank() > Score(80, 2, 3, True).rank()
    assert Score(80, 2, 2, False).rank() > Score(80, 2, 1, True).rank()
    assert Score(80, 2, 1, True).rank() > Score(80, 2, 1, False).rank()


def test_every_seat_including_trigger_gets_one_final_turn(monkeypatch):
    log = []
    def scripted_turn(self, game, player, final):
        log.append((player.id, final))
        if len(log) == 3:
            player.trains = 2
    monkeypatch.setattr(Bot, "take_turn", scripted_turn)
    result = play(*load_europe(), [Policy.named("regular")] * 4, seed=11)
    assert result.trigger == 2 and result.actions == 7
    assert log == [("0", False), ("1", False), ("2", False),
                   ("3", True), ("0", True), ("1", True), ("2", True)]


@pytest.mark.parametrize("seats", [2, 3, 4, 5])
def test_seeded_game_conserves_cards_trains_and_ownership(seats):
    policies = [Policy.named(n) for n in ("finish", "hoarder", "long", "regular", "adaptive")[:seats]]
    result = play(*load_europe(), policies, 200)
    g = result.game
    cards = Counter(g.deck.pile + g.deck.market + g.deck.discard)
    for p in g.players:
        assert all(n >= 0 for n in p.hand.values())
        assert p.trains + sum(r.length for r in p.routes) == 45
        assert all(g.state.route_owner[r.route_id] == p.id for r in p.routes)
        cards.update(p.hand)
    assert cards == {**dict.fromkeys(COLORS, 12), LOCO: 14}
    active = g.tickets + [t for p in g.players for t in p.tickets]
    assert len(set(active)) == len(active)


def test_replay_and_clock_control():
    board, tickets = load_europe()
    policy = Policy.named("regular")
    rows = tournament(board, tickets, policy, [policy] * 3, 4, 99, True)
    assert [r.seat for r in rows] == list(range(4))
    for row in rows:
        assert row.rounds == row.control_rounds
        assert row.opponent_points == row.control_cut_points == row.control_end_points
