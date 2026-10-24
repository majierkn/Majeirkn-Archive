"""Lógica de votação para skip democrático."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoteSession:
    """Sessão de votação para um servidor."""

    guild_id: int
    action: str  # "skip", "stop", etc.
    required_votes: int
    votes: set[int] = field(default_factory=set)

    def add_vote(self, user_id: int) -> bool:
        """Adiciona um voto. Retorna True se o usuário já havia votado."""
        already = user_id in self.votes
        self.votes.add(user_id)
        return already

    @property
    def vote_count(self) -> int:
        return len(self.votes)

    @property
    def passed(self) -> bool:
        return self.vote_count >= self.required_votes

    @property
    def progress(self) -> str:
        return f"{self.vote_count}/{self.required_votes}"


class VotingManager:
    """Gerencia sessões de votação por servidor."""

    def __init__(self) -> None:
        self._sessions: dict[int, VoteSession] = {}

    def start_vote(
        self,
        guild_id: int,
        action: str,
        required_votes: int,
        initiator_id: int,
    ) -> VoteSession:
        """Inicia uma nova votação (descarta a anterior para o mesmo servidor)."""
        session = VoteSession(
            guild_id=guild_id,
            action=action,
            required_votes=required_votes,
        )
        session.add_vote(initiator_id)
        self._sessions[guild_id] = session
        return session

    def get_session(self, guild_id: int) -> VoteSession | None:
        return self._sessions.get(guild_id)

    def add_vote(self, guild_id: int, user_id: int) -> VoteSession | None:
        """Adiciona um voto à sessão ativa. Retorna a sessão atualizada ou None."""
        session = self._sessions.get(guild_id)
        if session is None:
            return None
        session.add_vote(user_id)
        return session

    def end_vote(self, guild_id: int) -> None:
        """Encerra a sessão de votação do servidor."""
        self._sessions.pop(guild_id, None)

    def has_active_vote(self, guild_id: int) -> bool:
        return guild_id in self._sessions


def required_votes_for(member_count: int) -> int:
    """
    Calcula quantos votos são necessários para aprovação por maioria simples.

    member_count: número de membros humanos no canal de voz (excluindo bots e o DJ).
    """
    if member_count <= 0:
        return 1
    return (member_count // 2) + 1
