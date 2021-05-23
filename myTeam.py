from math import sqrt
from typing import Tuple

from capture import GameState
from captureAgents import CaptureAgent
import random, time

from distanceCalculator import Distancer
from game import Directions


def createTeam(
    firstIndex: int,
    secondIndex: int,
    isRed: bool,
    first: str = "DummyAgent",
    second: str = "DummyAgent",
):
    # The following line is an example only; feel free to change it.
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


def get_direction(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> Directions:
    if pos1[0] == pos2[0] and pos1[1] == pos2[1]:
        return Directions.STOP
    else:
        if pos1[0] == pos2[0]:
            if pos1[1] < pos2[1]:
                return Directions.NORTH
            else:
                return Directions.SOUTH
        else:
            if pos1[0] < pos2[0]:
                return Directions.EAST
            else:
                return Directions.WEST


class DummyAgent(CaptureAgent):
    is_pacman: bool = True

    def registerInitialState(self, gameState: GameState):
        CaptureAgent.registerInitialState(self, gameState)

        self.distancer = Distancer(gameState.data.layout)

        if self.red:
            self.enemies = gameState.getBlueTeamIndices()
        else:
            self.enemies = gameState.getRedTeamIndices()

        self.is_pacman = (
            self.index == (gameState.redTeam if self.red else gameState.blueTeam)[0]
        )

    def is_enemy_area(self, gameState: GameState, pos: Tuple[int, int]) -> bool:
        if self.red:
            return pos[0] >= gameState.data.layout.width / 2
        else:
            return pos[0] <= gameState.data.layout.width / 2

    def is_enemy_food(self, gameState: GameState, pos: Tuple[int, int]) -> bool:
        return gameState.data.food.data[pos[0]][pos[1]] and self.is_enemy_area(
            gameState=gameState, pos=pos
        )

    def get_current_pos(self, gameState: GameState) -> Tuple[int, int]:
        current_pos = gameState.data.agentStates[self.index].configuration.pos
        return int(current_pos[0]), int(current_pos[1])

    def get_possible_positions(self, gameState: GameState, noisy_distance):
        """
        Returns possible positions found by DFS from a set of noisy distances.
        """
        initial_pos = self.get_current_pos(gameState=gameState)
        possible_positions = []

        parent = {}
        stack = []
        current_pos = None
        stack.append(initial_pos)

        current_dist = 0
        # DFS search.
        while stack:
            current_pos = stack.pop(-1)
            current_dist += 1

            if current_dist == noisy_distance:
                possible_positions.append(current_pos)
                current_dist -= 1
                break

            adjacents = [
                (current_pos[0] - 1, current_pos[1]),
                (current_pos[0] + 1, current_pos[1]),
                (current_pos[0], current_pos[1] - 1),
                (current_pos[0], current_pos[1] + 1),
            ]

            for adj in adjacents:
                if (
                    # Within bounds and not wall.
                    0 <= adj[0] <= gameState.data.layout.width
                    and 0 <= adj[1] <= gameState.data.layout.height
                    and not gameState.data.layout.walls.data[adj[0]][adj[1]]
                    and adj not in parent.keys()
                ):
                    parent[adj] = current_pos
                    stack.append(adj)
                else:
                    current_dist -= 1
        return possible_positions

    def is_enemy_behind(self, gameState: GameState, target_pos: Tuple[int, int], enemy_pos: Tuple[int, int]) -> bool:
        # TODO: Check if enemy is behind the agent with respect to the direction of the target_pos.
        agent_pos = self.get_current_pos(gameState=gameState)
        target_x_dir, target_y_dir = agent_pos[0]-target_pos[0], agent_pos[1]-target_pos[1]
        enemy_x_dir, enemy_y_dir = agent_pos[0]-enemy_pos[0], agent_pos[1]-enemy_pos[1]
        return False

    def pos_reachable(self, gameState: GameState, target_pos: Tuple[int, int]) -> bool:
        # Check if this agent can reach a position before it gets eaten by an enemy ghost.
        agent_pos = self.get_current_pos(gameState=gameState)
        agent_target_dist = self.distancer.getDistance(agent_pos, target_pos)
        for enemy in self.enemies:
            get_enemy_pos = gameState.getAgentPosition(enemy)
            enemy_positions = []
            if get_enemy_pos is None:
                # Enemy is not in sight, estimate position.
                noisy_enemy_dist = gameState.getAgentDistances()[enemy]      # Get noisy enemy distance.
                possible_enemy_positions = self.get_possible_positions(gameState, noisy_enemy_dist)
                if not possible_enemy_positions:
                    # If no possible enemy position is found, return False.
                    # TODO: Return True instead?
                    return False
                enemy_positions = possible_enemy_positions
            else:
                # Exact enemy position is found.
                enemy_positions.append(get_enemy_pos)

            # Check if target can be reached before an enemy may reach it.
            for enemy_pos in enemy_positions:
                # if self.is_enemy_behind(gameState=gameState, target_pos=target_pos, enemy_pos=enemy_pos):
                #     # If enemy is behind it is not a threat.
                #     break
                enemy_target_dist = self.distancer.getDistance(enemy_pos, target_pos)
                if enemy_target_dist <= agent_target_dist:
                    # TODO: This check is not ideal since presumably the enemy chases the agent and not our target.
                    return False
        return True

    def get_power_ups(self, gameState: GameState):
        closest_power_up = None
        reachable_power_ups = []
        initial_pos = self.get_current_pos(gameState=gameState)
        if self.red:
            power_ups = gameState.getRedCapsules()
        else:
            power_ups = gameState.getBlueCapsules()
        # for capsule_pos in power_ups:
        #     # if self.pos_reachable(gameState=gameState, target_pos=capsule_pos):
        #     #     reachable_power_ups.append(capsule_pos)
        #     reachable_power_ups.append(capsule_pos)
        #
        # if reachable_power_ups:
        #     closest_power_up_dist = float('inf')
        #     for power_up in reachable_power_ups:
        #         power_up_dist = self.distancer.getDistance(initial_pos, power_up)
        #         if power_up_dist <= closest_power_up_dist:
        #             closest_power_up = power_up
        #             closest_power_up_dist = power_up_dist
        return power_ups

    def is_target(self, gameState: GameState, pos: Tuple[int, int]):
        if self.is_pacman:
            if any(
                [
                    a.configuration.pos[0] == pos[0]
                    and a.configuration.pos[1] == pos[1]
                    and a.scaredTimer > 5
                    for i, a in enumerate(gameState.data.agentStates)
                    if a.configuration
                    and (
                        (self.red and i in gameState.blueTeam)
                        or (not self.red and i in gameState.redTeam)
                    )
                    and a.isPacman
                    or pos in self.get_power_ups(gameState)                         # TODO: Is this written correctly?
                    and self.pos_reachable(gameState=gameState, target_pos=pos)     # TODO: Skip this check if power-up is active.
                ]
            ):
                return True
            else:
                if (
                    self.is_close_to_ghost(
                        gameState=gameState,
                        pos=self.get_current_pos(gameState=gameState),
                    )
                    or gameState.data.agentStates[self.index].numCarrying >= 9
                ):
                    return not self.is_enemy_area(gameState=gameState, pos=pos)
                else:
                    return self.is_enemy_food(gameState=gameState, pos=pos)
        else:   # Ghost
            if self.is_enemy_area(gameState=gameState, pos=pos):
                return False
            else:
                return any(
                    [
                        a.configuration.pos[0] == pos[0]
                        and a.configuration.pos[1] == pos[1]
                        for i, a in enumerate(gameState.data.agentStates)
                        if a.configuration
                        and (
                            (self.red and i in gameState.blueTeam)
                            or (not self.red and i in gameState.redTeam)
                        )
                        and a.isPacman
                    ]
                )

    def is_close_to_ghost(self, gameState: GameState, pos: Tuple[int, int]):
        return any(
            [
                sqrt(
                    pow(abs(a.configuration.pos[0] - pos[0]), 2)
                    + pow(abs(a.configuration.pos[1] - pos[1]), 2)
                )
                < 3
                for i, a in enumerate(gameState.data.agentStates)
                if a.configuration
                and (
                    (self.red and i in gameState.blueTeam)
                    or (not self.red and i in gameState.redTeam)
                )
                and not a.isPacman
            ]
        )

    def chooseAction(self, gameState: GameState):
        time.sleep(0.0025)
        initial_pos = self.get_current_pos(gameState=gameState)
        actions = gameState.getLegalActions(self.index)

        parent = {}
        queue = []
        current_pos = None
        queue.append(initial_pos)

        while queue:
            current_pos = queue.pop(0)

            if self.is_target(gameState=gameState, pos=current_pos):
                break

            adjacents = [
                (current_pos[0] - 1, current_pos[1]),
                (current_pos[0] + 1, current_pos[1]),
                (current_pos[0], current_pos[1] - 1),
                (current_pos[0], current_pos[1] + 1),
            ]

            for adj in adjacents:
                if (
                    0 <= adj[0] <= gameState.data.layout.width
                    and 0 <= adj[1] <= gameState.data.layout.height
                    and not gameState.data.layout.walls.data[adj[0]][adj[1]]
                    and adj not in parent.keys()
                    and (
                        self.is_pacman
                        or not self.is_enemy_area(gameState=gameState, pos=adj)
                    )
                ):
                    parent[adj] = current_pos
                    queue.append(adj)

        if current_pos:
            while current_pos in parent.keys() and parent[current_pos] != initial_pos:
                current_pos = parent[current_pos]
            return get_direction(initial_pos, current_pos)
        return random.choice(actions)
