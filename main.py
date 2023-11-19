import tkinter as tk
from pygame import mixer

class Game():

    def __init__(self):
        # create window
        self.window = tk.Tk()
        self.window.title("Rhythm Conquid")
        self.window.configure(width=1000, height=600)
        self.board = Board(self.window)
        self.window.after(self.board.clock.music_track.offset,self.board.clock.cycle)
        self.window.mainloop()

class Board(tk.Frame):
    # board dimensions in tiles
    horiz_t = 28
    vert_t = 14

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.pack()
        # generate tiles
        for i in range(self.vert_t):
            for j in range(self.horiz_t):
                newtile = Tile(self,(i,j))
                newtile.grid(row=i,column=j,padx=3,pady=3)
                # give neighbour references
                if i>0:
                    newtile.add_neighbour(self.tile_at(i-1,j))
                if j>0:
                    newtile.add_neighbour(self.tile_at(i,j-1))
        self.updates = [] # list of each consecutive board update through the game
        self.players = [Player(("red","maroon","orange")),Player(("blue","navy","cyan"))] # list of players in turn order
        self.turn = 0 # number of turns carried out
        self.clock = Clock(self,routine="+++=--",pulse="=++++++-") # the clock that runs the timing behind the game
        self.curr_move = Move(self, self.players[self.turn]) # object that represents the current move being taken
        # add bases to the board
        bases = ((self.players[0],True),(self.players[1],True),(None,True))
        initial_update = {}
        for i in range(6,8):
            for j in range(4,6):
                initial_update[self.tile_at(i,j)] = bases[0]
                bases[0][0].base.append(self.tile_at(i,j))
                initial_update[self.tile_at(i,self.horiz_t-j-1)] = bases[1]
                bases[1][0].base.append(self.tile_at(i,self.horiz_t-j-1))
        self.apply_update(initial_update)

    # applies the changes listed in an update to the board
    def apply_update(self, update):
        self.updates.append(update)
        for tile in update:
            tile.update_owner(update[tile][0], update[tile][1], False)

    # adds an input onto the current move if allowed
    def build_move(self, tile):
        if self.clock.accepting():
            self.curr_move.add_input(tile)

    # submits the current move's update if completed
    def submit_move(self):
        if self.curr_move.completed():
            self.apply_update(self.curr_move.update)
        self.turn+=1
        self.curr_move = Move(self, self.players[self.turn%len(self.players)])

    # returns tile at grid index
    def tile_at(self, i, j):
        return self.grid_slaves(row=i, column=j)[0] if (i>=0 and j>=0 and i<self.vert_t and j<self.horiz_t) else None


class Tile(tk.Button):

    generic_colors = ("silver", "gray", "light gray")  # colors of unoccupied tiles [tile, base, flash]

    def __init__(self, parent, gix):
        self.pixel = tk.PhotoImage(width=1, height=1) # image so tile sizes in pixels
        tk.Button.__init__(self, parent, height=50,width=50,bg=self.generic_colors[0],activebackground=self.generic_colors[1],relief=tk.FLAT,command=self.press,image=self.pixel)
        self.grid_ix = gix # index of this tile on the board
        # change border type when cell is hovered
        self.bind("<Enter>", func=lambda e: self.config(relief=tk.RAISED))
        self.bind("<Leave>", func=lambda e: self.config(relief=tk.FLAT))
        #self.state = 0
        #self.tile_colors = ["silver","red","blue","cyan","orange"]
        self.owner = None # player that owns this tile
        self.base = False # if the tile is unalterable (if true, tile is a base or a wall)
        self.neighbours = [] # tiles that neighbour this one
        self.flash = False # if color should be overridden for a flash effect

    # interpret tile click
    def press(self):
        self.master.build_move(self)

    # change the owner of this tile
    def update_owner(self, owner, base, flash):
        self.owner = owner
        self.base = base
        self.flash = flash
        self.config(bg=self.display_color())

    # display color based on owner and base
    def display_color(self):
        colors = self.generic_colors
        if self.owner is not None:
            colors = self.owner.colors
        return colors[2] if self.flash else colors[1] if self.base else colors[0]

    # connects two tiles as neighbors
    def add_neighbour(self, neigh):
        self.neighbours.append(neigh)
        neigh.neighbours.append(self)

class Move():

    submit_length = 3 # number of inputs per turn
    vanquish_size = 4 # dimensions of square that gets vanquished and number of neighbours needed

    def __init__(self, board, player):
        self.inputs = [] # tiles clicked for this move
        self.update = {} # tiles and their corresponding new owners once the move is implemented
        self.player = player # player doing this move
        self.board = board # board being acted upon

    # add another tile click to move and process if needed
    def add_input(self, tile):
        #self.update[tile] = state
        #self.update[tile] = self.player
        self.inputs.append(tile)
        if self.completed():
            self.calculate_update()

    # whether the move is ready for submission
    def completed(self):
        return len(self.inputs) >= self.submit_length

    # using the inputs, calculate the tile updates for the appropriate type of turn
    def calculate_update(self):
        blank = 0
        own_base = 0
        other_base = 0
        turf = 0
        for tile in self.inputs:
            if tile.base:
                if tile.owner == self.player:
                    own_base+=1
                else:
                    other_base+=1
            else:
                turf+=1
                if tile.owner is None:
                    blank += 1
        if self.can_acquire(blank):
            self.acquire()
        elif self.can_conquer(own_base):
            self.conquer()
        elif self.can_conquest(own_base, other_base):
            self.conquest()
        elif self.can_vanquish(turf, own_base):
            self.vanquish()
        else:
            self.skip()

    def can_acquire(self, blank):
        return blank == len(self.inputs) and blank <= self.submit_length
    def can_conquer(self, own_base):
        return own_base == self.submit_length
    def can_conquest(self, own_base, other_base):
        return own_base + other_base == self.submit_length
    def can_vanquish(self, turf, own_base):
        # input sequence correct
        if turf!=2 or turf + own_base != self.submit_length:
            return False
        tiles = []
        for tile in self.inputs:
            if not tile.base:
                tiles.append(tile)
        # not correct dimensions
        if abs(tiles[0].grid_ix[0] - tiles[1].grid_ix[0]) != self.vanquish_size-1:
            return False
        if abs(tiles[0].grid_ix[1] - tiles[1].grid_ix[1]) != self.vanquish_size-1:
            return False
        mini = min(tiles[0].grid_ix[0], tiles[1].grid_ix[0])
        maxi = max(tiles[0].grid_ix[0], tiles[1].grid_ix[0])
        minj = min(tiles[0].grid_ix[1], tiles[1].grid_ix[1])
        maxj = max(tiles[0].grid_ix[1], tiles[1].grid_ix[1])
        # not solid block of one owner
        for i in range(mini, maxi+1):
            for j in range(minj, maxj+1):
                if self.board.tile_at(i,j) and tiles[0].owner != self.board.tile_at(i,j).owner:
                    return False
        # not enough tiles bordering
        vanquishers = 0
        for i in range(mini, maxi+1):
            if self.board.tile_at(i, minj-1) and self.player == self.board.tile_at(i, minj-1).owner:
                vanquishers += 1
            if self.board.tile_at(i, maxj+1) and self.player == self.board.tile_at(i, maxj+1).owner:
                vanquishers += 1
        for j in range(minj, maxj+1):
            if self.board.tile_at(mini-1, j) and self.player == self.board.tile_at(mini-1, j).owner:
                vanquishers += 1
            if self.board.tile_at(maxi+1, j) and self.player == self.board.tile_at(maxi+1, j).owner:
                vanquishers += 1
        return vanquishers >= self.vanquish_size



    # claim individual tiles
    def acquire(self):
        self.update = {}
        # invalid if contains duplicates
        #if len(set(self.inputs)) != len(self.inputs):
        #    return
        for tile in self.inputs:
            self.update[tile] = (self.player, False)

    # use tiles to take over their neighbours
    def conquer(self):
        self.update = {}

        # determine whether tile can be used to conquer or if it can be conquered
        def is_attacker(tile):
            return (tile.owner == self.player and not tile.base) or tile in self.update
        def is_target(tile):
            return tile.owner is not None and tile.owner != self.player and tile not in self.update and not tile.base

        # recursive step of checking a tile, converting it if conquerable, and checking its neighbours
        def check(tile):
            if is_target(tile):
                surrounds = 0
                frees = []
                for nt in tile.neighbours:
                    if is_attacker(nt):
                        surrounds += 1
                    elif is_target(nt):
                        frees.append(nt)
                if surrounds >= 2:
                    self.update[tile] = (self.player, False)
                    for nt in frees:
                        check(nt)
            elif is_attacker(tile):
                for nt in tile.neighbours:
                    if is_target(nt):
                        check(nt)

        # initiate checking on all of the conquerer's tiles
        for tile in self.board.grid_slaves():
            if is_attacker(tile):
                check(tile)

    # attempt to bridge between bases
    def conquest(self):
        self.update = {}
        failed = set()
        stack = []
        # start at current base
        stack.append(self.player.base[0])

        # neighbours that can be moved to for conquest
        def valid_neighbours(tile):
            return [nt for nt in tile.neighbours if nt.owner == self.player and nt not in failed and nt not in stack]

        # if the bases have been linked
        def is_success(tile):
            return len([nt for nt in tile.neighbours if nt.owner is not None and nt.owner != self.player and nt.base]) > 0

        # move down branches and pop back until success
        while stack and not is_success(stack[-1]):
            neighbs = valid_neighbours(stack[-1])
            if neighbs:
                stack.append(neighbs[0])
            else:
                failed.add(stack[-1])
                stack.pop()

        # turn path into bases
        for tile in stack:
            self.update[tile] = (self.player, True)

    # use tiles to delete block of a cell type
    def vanquish(self):
        self.update = {}
        tiles = []
        for tile in self.inputs:
            if not tile.base:
                tiles.append(tile)
        mini = min(tiles[0].grid_ix[0], tiles[1].grid_ix[0])
        maxi = max(tiles[0].grid_ix[0], tiles[1].grid_ix[0])
        minj = min(tiles[0].grid_ix[1], tiles[1].grid_ix[1])
        maxj = max(tiles[0].grid_ix[1], tiles[1].grid_ix[1])
        for i in range(mini,maxi+1):
            for j in range(minj,maxj+1):
                self.update[self.board.tile_at(i,j)] = (None, False)


    # invalid move, no update
    def skip(self):
        self.update = {}


class Player():
    def __init__(self, color):
        self.colors = color
        self.base = []

    #
    def flash_base(self, toggle):
        for b in self.base:
            b.update_owner(self, True, toggle)

class Clock():
    def __init__(self, board, routine, pulse):
        self.board = board
        self.routine = routine # keeps track of which beats are for inputs
        self.pulse = pulse # keeps track of which part of a beat counts for inputs
        self.r_pos = -1
        self.timing = 125 # timing between pulses
        self.p_pos = 0
        self.r_beat = "-"
        self.p_beat = "-"
        self.flash = False
        mixer.init()
        self.do_sound = mixer.Sound("resources/do.mp3")
        self.dont_sound = mixer.Sound("resources/dont.mp3")
        self.music_track = Track("resources/crinolinedreams.mp3", 0, self.timing)

    # main clock cycle
    def cycle(self):

        if not self.music_track.is_playing():
            self.music_track.play()

        def pulse(p_beat):
            #print(self.p_beat, self.r_beat)
            if p_beat == "=":
                self.r_pos += 1
                if self.r_pos >= len(self.routine):
                    self.r_pos = 0
                self.r_beat = self.routine[self.r_pos]

                r_beat = self.r_beat

                # submit updates
                if r_beat == "=":
                    self.board.submit_move()

                # play sound
                if r_beat == "+":
                    self.do_sound.play()
                else:
                    self.dont_sound.play()

            # flash background on beat
            if p_beat == "+" and not self.flash:
                self.flash = True
                self.board.configure(bg="gainsboro")
            if p_beat == "-" and self.flash:
                self.flash = False
                self.board.configure(bg="light gray")

            # flash base on turn
            self.board.curr_move.player.flash_base(self.accepting())

        self.p_pos += 1
        if self.p_pos >= len(self.pulse):
            self.p_pos = 0
        self.p_beat = self.pulse[self.p_pos]
        pulse(self.p_beat)

        time_to_next = self.music_track.next_checkpoint()
        # print(time_to_next)
        if time_to_next < self.timing * .5:
            self.board.master.after(self.timing+time_to_next, self.cycle)
        else:
            self.board.master.after(time_to_next, self.cycle)
        #self.board.master.after(self.timing, self.cycle)

    # if inputs can be received for moves
    def accepting(self):
        return self.p_beat == self.r_beat == "+"

class Track():
    def __init__(self, title, offset, millis):
        mixer.music.load(title)
        self.offset = offset
        self.millis = millis
        self.playing = False

    def play(self):
        mixer.music.play(loops = -1)

    def next_checkpoint(self):
        return self.millis - ((mixer.music.get_pos() + self.offset) % self.millis)

    def is_playing(self):
        #return mixer.get_busy()
        if self.playing:
            return True
        else:
            self.playing = True
            return False

Game()
