"""Testes para o módulo core/voting.py."""

import pytest

from core.voting import VotingManager, required_votes_for


class TestRequiredVotes:
    def test_single_member(self) -> None:
        assert required_votes_for(1) == 1

    def test_two_members(self) -> None:
        assert required_votes_for(2) == 2

    def test_three_members(self) -> None:
        assert required_votes_for(3) == 2

    def test_four_members(self) -> None:
        assert required_votes_for(4) == 3

    def test_zero_members(self) -> None:
        assert required_votes_for(0) == 1

    def test_large_group(self) -> None:
        # Maioria simples: 10 → 6
        assert required_votes_for(10) == 6


class TestVotingManager:
    def test_start_vote(self) -> None:
        vm = VotingManager()
        session = vm.start_vote(guild_id=1, action="skip", required_votes=3, initiator_id=100)
        assert session.vote_count == 1
        assert session.action == "skip"
        assert not session.passed

    def test_vote_passes(self) -> None:
        vm = VotingManager()
        session = vm.start_vote(guild_id=2, action="skip", required_votes=2, initiator_id=100)
        vm.add_vote(2, 200)
        assert session.passed

    def test_duplicate_vote_ignored(self) -> None:
        vm = VotingManager()
        session = vm.start_vote(guild_id=3, action="skip", required_votes=3, initiator_id=100)
        already = session.add_vote(100)  # mesmo usuário
        assert already
        assert session.vote_count == 1

    def test_end_vote(self) -> None:
        vm = VotingManager()
        vm.start_vote(guild_id=4, action="skip", required_votes=2, initiator_id=100)
        assert vm.has_active_vote(4)
        vm.end_vote(4)
        assert not vm.has_active_vote(4)

    def test_add_vote_no_session(self) -> None:
        vm = VotingManager()
        result = vm.add_vote(guild_id=99, user_id=100)
        assert result is None

    def test_progress_string(self) -> None:
        vm = VotingManager()
        session = vm.start_vote(guild_id=5, action="skip", required_votes=3, initiator_id=100)
        assert session.progress == "1/3"

    def test_overwrite_previous_vote(self) -> None:
        vm = VotingManager()
        vm.start_vote(guild_id=6, action="skip", required_votes=3, initiator_id=100)
        # Nova votação sobrescreve a anterior
        session2 = vm.start_vote(guild_id=6, action="stop", required_votes=2, initiator_id=200)
        assert session2.action == "stop"
        assert session2.vote_count == 1
