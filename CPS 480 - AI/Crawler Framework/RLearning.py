
"""
@author: Ju Shen
@email: jshen1@udayton.edu
@date: 02-16-2026
"""
import random
import numpy as np
import math as mth

# The state class
class State:
    def __init__(self, angle1=0, angle2=0):
        self.angle1 = angle1
        self.angle2 = angle2

class ReinforceLearning:

    #
    def __init__(self, unit=5):

        ####################################  Needed: here are the variable to use  ################################################

        # The crawler agent
        self.crawler = 0

        # Number of iterations for learning
        self.steps = 1000

        # learning rate alpha
        self.alpha = 0.2

        # Discounting factor
        self.gamma = 0.95

        # E-greedy probability
        self.epsilon = 0.1

        # Small optimistic start helps exploration when most Q-values are still untouched
        self.q_init = 0.05

        self.Qvalue = []  # Update Q values here
        self.unit = unit  # 5-degrees
        self.angle1_range = [-35, 55]  # specify the range of "angle1"
        self.angle2_range = [0, 180]  # specify the range of "angle2"
        self.rows = int(1 + (self.angle1_range[1] - self.angle1_range[0]) / unit)  # the number of possible angle 1
        self.cols = int(1 + (self.angle2_range[1] - self.angle2_range[0]) / unit)  # the number of possible angle 2

        ########################################################  End of Needed  ################################################



        self.pi = [] # store policies
        self.actions = [-1, +1] # possible actions for each angle

        # Controlling Process
        self.learned = False



        # Initialize all the Q-values
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                for a in range(9):
                    row.append(self.q_init)
            self.Qvalue.append(row)



        # Initialize all the action combinations
        self.actions = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1))


        # Initialize the policy
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                row.append(random.randint(0, 8))
            self.pi.append(row)

    def _best_action_index(self, r, c):
        best_value = max(self.Qvalue[r][c * 9 + i] for i in range(9))
        best_indices = [i for i in range(9) if self.Qvalue[r][c * 9 + i] == best_value]
        return random.choice(best_indices)

    # Reset the learner to empty
    def reset(self):
        self.Qvalue = [] # store Q values
        self.R = [] # not working
        self.pi = [] # store policies

        # Initialize all the Q-values
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                for a in range(9):
                    row.append(self.q_init)
            self.Qvalue.append(row)

        # Initiliaize all the Reward
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                for a in range(9):
                    row.append(0.0)
            self.R.append(row)

        # Initialize all the action combinations
        self.actions = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1))


        # Initialize the policy
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                row.append(random.randint(0, 8))
            self.pi.append(row)

        # Controlling Process
        self.learned = False

    # Set the basic info about the robot
    def setBot(self, crawler):
        self.crawler = crawler

    def storeCurrentStatus(self):
        self.old_location = self.crawler.location
        self.old_angle1 = self.crawler.angle1
        self.old_angle2 = self.crawler.angle2
        self.old_contact = self.crawler.contact
        self.old_contact_pt = self.crawler.contact_pt
        self.old_location = self.crawler.location
        self.old_p1 = self.crawler.p1
        self.old_p2 = self.crawler.p2
        self.old_p3 = self.crawler.p3
        self.old_p4 = self.crawler.p4
        self.old_p5 = self.crawler.p5
        self.old_p6 = self.crawler.p6

    def reverseStatus(self):
        self.crawler.location = self.old_location
        self.crawler.angle1 = self.old_angle1
        self.crawler.angle2 = self.old_angle2
        self.crawler.contact = self.old_contact
        self.crawler.contact_pt = self.old_contact_pt
        self.crawler.location = self.old_location
        self.crawler.p1 = self.old_p1
        self.crawler.p2 = self.old_p2
        self.crawler.p3 = self.old_p3
        self.crawler.p4 = self.old_p4
        self.crawler.p5 = self.old_p5
        self.crawler.p6 = self.old_p6

    def updatePolicy(self):
        # After convergence, generate policy y
        for r in range(self.rows):
            for c in range(self.cols):
                self.pi[r][c] = self._best_action_index(r, c)

    # This function will do additional saving of current states than Q-learning
    def onLearningProxy(self, option):
        self.storeCurrentStatus()
        if option == 0:
            self.onMonteCarlo()
        elif option == 1:
            self.onTDLearning()
        elif option == 2:
            self.onQLearning()
        self.reverseStatus()


        # Turn off learned
        self.learned = True

    # For the play_btn uses: choose an action based on the policy pi
    def onPlay(self, ang1, ang2, mode=1):

        epsilon = self.epsilon

        ang1_cur = ang1
        ang2_cur = ang2

        # get the state index
        r = int((ang1_cur - self.angle1_range[0]) / self.unit)
        c = int((ang2_cur - self.angle2_range[0]) / self.unit)

        # Choose an action and udpate the angles
        idx, angle1_update, angle2_update = self.chooseAction(r=r, c=c)
        ang1_cur += self.unit * angle1_update
        ang2_cur += self.unit * angle2_update

        return ang1_cur, ang2_cur



        ####################################  Required: core functions used by learning  ################################################

        # epsilon = exploration probability
        # gamma = discount factor
        # alpha = step size (learning rate)

        # This behaves like "runReward()" but does not compute or return a reward.
        # It simply updates robot pose from the given "angle1" and "angle2".
    def setBotAngles(self, ang1, ang2):
        self.crawler.angle1 = ang1
        self.crawler.angle2 = ang2
        self.crawler.posConfig()

        # Method 1: Monte Carlo control
    def onMonteCarlo(self):
        """
                On-policy Monte Carlo control using epsilon-greedy action selection.
        For each episode:
                    1. Roll out a trajectory under the current epsilon-greedy policy.
                    2. Compute total return G (crawler x-displacement).
                    3. Update each visited (state, action) pair.
        """

        epsilon = self.epsilon
        gamma   = self.gamma

        # Returns can be accumulated and averaged incrementally across episodes.
        # Here we reuse Qvalue directly with an incremental mean-style update.

        # self.steps determines how many episodes are run (one loop iteration = one episode).
        num_episodes = self.steps

        for _ in range(num_episodes):

            # --- 1. Roll out one episode ---
            # Begin from the crawler's current state (saved/restored outside this method).
            ang1 = self.crawler.angle1
            ang2 = self.crawler.angle2
            init_x = self.crawler.location[0]

            trajectory = []  # stores (r, c, action_idx, angle1_update, angle2_update)

            # Sample episode length uniformly between 5 and 30 steps.
            episode_len = random.randint(5, 30)

            for _ in range(episode_len):
                r = int((ang1 - self.angle1_range[0]) / self.unit)
                c = int((ang2 - self.angle2_range[0]) / self.unit)

                # Keep state indices inside valid bounds.
                r = max(0, min(r, self.rows - 1))
                c = max(0, min(c, self.cols - 1))

                idx, a1_upd, a2_upd = self.chooseAction(r, c)
                trajectory.append((r, c, idx))

                # Apply selected action to the crawler.
                new_ang1 = ang1 + a1_upd * self.unit
                new_ang2 = ang2 + a2_upd * self.unit
                self.setBotAngles(new_ang1, new_ang2)
                ang1 = self.crawler.angle1
                ang2 = self.crawler.angle2

            # --- 2. Compute episode return as x-displacement ---
            final_x = self.crawler.location[0]
            G = final_x - init_x   # positive means forward (to the right)

            # --- 3. First-visit MC update for visited (state, action) pairs ---
            visited = set()
            for (r, c, idx) in trajectory:
                key = (r, c, idx)
                if key not in visited:
                    visited.add(key)
                    col = c * 9 + idx
                    # Incremental update: Q <- Q + alpha * (G - Q)
                    self.Qvalue[r][col] += self.alpha * (G - self.Qvalue[r][col])

        return


        # Method 2: Online TD learning with SARSA
    def onTDLearning(self):
        """
                On-policy TD control via SARSA.
        For each step in self.steps:
                    - Select action A from state S with epsilon-greedy.
                    - Execute it, observe reward r and next state S'.
                    - Select next action A' from S' with epsilon-greedy.
                    - Update: Q(S,A) <- Q(S,A) + alpha * [r + gamma*Q(S',A') - Q(S,A)]
        """

        epsilon = self.epsilon
        gamma   = self.gamma
        alpha   = self.alpha

        ang1 = self.crawler.angle1
        ang2 = self.crawler.angle2

        for _ in range(self.steps):
            r = int((ang1 - self.angle1_range[0]) / self.unit)
            c = int((ang2 - self.angle2_range[0]) / self.unit)
            r = max(0, min(r, self.rows - 1))
            c = max(0, min(c, self.cols - 1))

            # Select action A using epsilon-greedy.
            idx, a1_upd, a2_upd = self.chooseAction(r, c)

            # Save x-position before applying the action.
            old_x = self.crawler.location[0]

            # Execute action.
            new_ang1 = ang1 + a1_upd * self.unit
            new_ang2 = ang2 + a2_upd * self.unit
            self.setBotAngles(new_ang1, new_ang2)

            # Reward equals x-position delta.
            reward = self.crawler.location[0] - old_x

            # Read next state.
            ang1_next = self.crawler.angle1
            ang2_next = self.crawler.angle2
            r_next = int((ang1_next - self.angle1_range[0]) / self.unit)
            c_next = int((ang2_next - self.angle2_range[0]) / self.unit)
            r_next = max(0, min(r_next, self.rows - 1))
            c_next = max(0, min(c_next, self.cols - 1))

            # Select next action A' (SARSA uses the behavior action actually taken).
            idx_next, _, _ = self.chooseAction(r_next, c_next)

            # SARSA temporal-difference update.
            q_current = self.Qvalue[r][c * 9 + idx]
            q_next    = self.Qvalue[r_next][c_next * 9 + idx_next]
            self.Qvalue[r][c * 9 + idx] += alpha * (reward + gamma * q_next - q_current)

            ang1 = ang1_next
            ang2 = ang2_next

        return

    # From the current state, return action index plus angle1/angle2 deltas.
    # Return values:
    #  - index: integer in [0, 8], indicating the chosen epsilon-greedy action
    #  - angle1_update: -1, 0, or +1
    #  - angle2_update: -1, 0, or +1
    def chooseAction(self, r, c):
        """
        Select an action with epsilon-greedy.
        With probability epsilon: pick a random action index (0-8).
        With probability 1-epsilon: pick a greedy (max-Q) action index.
        """

        epsilon = self.epsilon

        # Explore with probability epsilon.
        if random.random() < epsilon:
            idx = random.randint(0, 8)
        else:
            # Exploit greedily; random tie-break keeps equal-valued options from collapsing.
            idx = self._best_action_index(r, c)

        (angle1_update, angle2_update) = self.actions[idx]

        # If an action exceeds bounds, clamp that component to 0 (no movement on that axis).
        if angle1_update * self.unit + self.crawler.angle1 < self.angle1_range[0] or \
           angle1_update * self.unit + self.crawler.angle1 > self.angle1_range[1]:
            angle1_update = 0

        if angle2_update * self.unit + self.crawler.angle2 < self.angle2_range[0] or \
           angle2_update * self.unit + self.crawler.angle2 > self.angle2_range[1]:
            angle2_update = 0

        return idx, angle1_update, angle2_update


        # Method 3: Online TD learning with Bellman target (Q-learning)
    def onQLearning(self):
        """
                Off-policy TD control with Q-learning (Bellman backup).
        For each step in self.steps:
                    - Select action A from state S via epsilon-greedy.
                    - Execute it, observe reward r and next state S'.
                    - Update: Q(S,A) <- Q(S,A) + alpha * [r + gamma * max_a Q(S',a) - Q(S,A)]
                Main contrast with SARSA: the target uses max over next actions (off-policy).
        """

        epsilon = self.epsilon
        gamma   = self.gamma
        alpha   = self.alpha

        ang1 = self.crawler.angle1
        ang2 = self.crawler.angle2

        for _ in range(self.steps):
            r = int((ang1 - self.angle1_range[0]) / self.unit)
            c = int((ang2 - self.angle2_range[0]) / self.unit)
            r = max(0, min(r, self.rows - 1))
            c = max(0, min(c, self.cols - 1))

            # Select behavior-policy action A via epsilon-greedy.
            idx, a1_upd, a2_upd = self.chooseAction(r, c)

            # Save x-position before applying action.
            old_x = self.crawler.location[0]

            # Execute action.
            new_ang1 = ang1 + a1_upd * self.unit
            new_ang2 = ang2 + a2_upd * self.unit
            self.setBotAngles(new_ang1, new_ang2)

            # Reward is the x-position change.
            reward = self.crawler.location[0] - old_x

            # Read next state.
            ang1_next = self.crawler.angle1
            ang2_next = self.crawler.angle2
            r_next = int((ang1_next - self.angle1_range[0]) / self.unit)
            c_next = int((ang2_next - self.angle2_range[0]) / self.unit)
            r_next = max(0, min(r_next, self.rows - 1))
            c_next = max(0, min(c_next, self.cols - 1))

            # Q-learning target uses max Q over all next actions (greedy target policy).
            max_q_next = max(self.Qvalue[r_next][c_next * 9 + i] for i in range(9))

            q_current = self.Qvalue[r][c * 9 + idx]
            self.Qvalue[r][c * 9 + idx] += alpha * (reward + gamma * max_q_next - q_current)

            ang1 = ang1_next
            ang2 = ang2_next

        return

