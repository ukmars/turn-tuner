import tkinter as tk
from tkinter import ttk
import math
import copy
from dataclasses import dataclass

turn_names = ["SS90E",
              "SS90F",
              "SS180",
              "SD45",
              "SD135",
              "DS45",
              "DS135",
              "DD90",
              ]


@dataclass
class TurnParameters:
    pivot_x: float = 0.0
    pivot_y: float = 0.0
    arc_radius: float = 0.0
    delta: float = 0.0
    offset: float = 0.0
    start_angle: float = 0.0
    angle: float = 0.0
    speed: float = 0.0

    def __repr__(self):
        s = f"       pivot: ({self.pivot_x:.0f},{self.pivot_y:.0f})\n"
        s += f"  max. speed: {self.speed:.0f}\n"
        s += f"  arc radius: {self.arc_radius:.0f}\n"
        s += f"       delta: {self.delta:.0f}\n"
        s += f"      offset: {self.offset:.0f}\n"
        s += f" start angle: {self.start_angle:.0f}\n"
        s += f"  turn angle: {self.angle:.0f}\n"
        return s


default_params = {
    "SS90E": TurnParameters(pivot_x=270, pivot_y=270, offset=75, delta=36, arc_radius=57, start_angle=0, angle=90),
    "SS90F": TurnParameters(pivot_x=270, pivot_y=270, offset=85, delta=36, arc_radius=67, start_angle=0, angle=90),
    "SS180": TurnParameters(pivot_x=270, pivot_y=270, offset=120, delta=40, arc_radius=89, start_angle=0, angle=180),
    "SD45": TurnParameters(pivot_x=270, pivot_y=270, offset=140, delta=39, arc_radius=73, start_angle=0, angle=45),
    "SD135": TurnParameters(pivot_x=270, pivot_y=270, offset=150, delta=74, arc_radius=83, start_angle=0, angle=135),
    "DS45": TurnParameters(pivot_x=180, pivot_y=270, offset=84, delta=50, arc_radius=145, start_angle=45, angle=45),
    "DS135": TurnParameters(pivot_x=180, pivot_y=270, offset=105, delta=90, arc_radius=74, start_angle=45, angle=135),
    "DD90": TurnParameters(pivot_x=180, pivot_y=270, offset=94, delta=59, arc_radius=63, start_angle=45, angle=90),
}

working_params = copy.deepcopy(default_params)


class Application(tk.Tk):
    def __init__(self, title, size):
        # main setup
        super().__init__()
        self.main_title = 'UKMARSBOT Turn Calculator'
        self.title(self.main_title)
        self.geometry(f'{size[0]}x{size[1]}')
        self.minsize(size[0], size[1])
        img = tk.PhotoImage(file='turn_setting.png')
        self.iconphoto(False, img)
        # parameters
        self.working_params = copy.deepcopy(default_params)
        self.current_turn = turn_names[0]
        self.current_params = working_params[self.current_turn]
        # widgets
        # reserve a space for the declaration later
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side='bottom')
        # The three main components
        self.maze_frame = MazeFrame(self)
        self.settings = Settings(self)
        self.turn_selector = TurnSelector(self)
        # and a c declaration to copy
        self.c_declaration = tk.StringVar(value = "{TURN_SPEED, 20, 10, 90, 287, 2866, TRIGGER}")
        lbl_declaration = tk.Entry(bottom_frame,width = 50,
                                   textvariable=self.c_declaration,
                                   font= ('consolas 10'),
                                   state='readonly')
        lbl_declaration.pack(side='bottom',expand=True, fill='x',  padx=5, pady=5)
        # convenience values
        self.maze_offs_x = self.maze_frame.maze_view.origin_x()
        self.maze_offs_y = self.maze_frame.maze_view.origin_y()
        # objects
        self.robot = Robot(self.maze_frame.maze_view)
        self.robot.draw(self.maze_offs_x, self.maze_offs_y)
        self.profile = TurnProfile(self.settings)

        # run
        self.refresh()
        self.mainloop()

    def refresh(self):
        # work out which turn we are using
        self.current_turn = self.turn_selector.name.get()
        self.title(self.main_title + ' - ' + self.current_turn)
        self.maze_frame.turn_name.set(self.current_turn)
        # print(self.current_params)
        global working_params
        working_params[self.current_turn].offset = self.settings.g_turn_offset.get()
        working_params[self.current_turn].delta = self.settings.g_turn_delta.get()
        working_params[self.current_turn].arc_radius = self.settings.g_turn_radius.get()

        self.current_params = working_params[self.current_turn]
        self.profile.set_parameters(self.current_params)
        self.profile.set_speed(float(self.settings.g_turn_speed.get()))
        self.profile.set_radius(float(self.settings.g_turn_radius.get()))
        self.profile.set_delta(float(self.settings.g_turn_delta.get()))
        (omega, alpha, t3, v_max) = self.profile.calculate()
        self.settings.g_turn_omega.set(F'OMEGA = {omega:5.1f} deg/s')
        self.settings.g_turn_alpha.set(F'ALPHA = {alpha:6.1f} deg/s/s')
        self.settings.g_turn_time.set(F'TIME = {t3:5.3f} s')
        # assuming max centripetal acceleration, how fast can we go?
        max_available_speed = math.sqrt(1234)
        MAX_CENTRIPETAL_ACC = 5000
        self.settings.g_turn_speed_max.set(
            F'MAX SPEED = {v_max:4.0f} mm/s \n(for {MAX_CENTRIPETAL_ACC:4.0f} mm/s/s acceleration)')
        decl = '{TURN_SPEED, '
        decl += F"{self.current_params.offset:3d}, "
        decl += F"{self.current_params.offset:3d}, "
        decl += F"{omega:4.1f}, "
        decl += F"{alpha:4.1f}, "
        decl += "TRIGGER},"

        # self.c_declaration.set("{TURN_SPEED, {20, 10, 90, 287, 2866, TRIGGER}")
        self.c_declaration.set(decl)

        self.maze_frame.maze_view.clear()
        self.profile.draw(self.maze_frame.maze_view)
        angle = self.current_params.start_angle
        offset = self.current_params.offset
        robot_x = self.current_params.pivot_x + offset * math.sin(math.radians(angle))
        robot_y = self.current_params.pivot_y - offset * math.cos(math.radians(angle))
        self.robot.set_pose(Pose(robot_x, robot_y, angle))
        self.robot.draw(self.maze_frame.maze_view.origin_x(),self.maze_frame.maze_view.origin_y())

        print('updated ' + self.current_turn)
        # print(self.current_params)


class TurnSelector(tk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pack(side='left', expand=True, fill='both', padx=5, pady=5)
        self.configure(text='Turn Type')
        self.name = tk.StringVar()
        self.buttons = []
        rb_options = {'anchor': 'w'}
        for index, name in enumerate(turn_names):
            self.buttons.append(tk.Radiobutton(self,
                                               text=name,
                                               variable=self.name,
                                               value=name,
                                               command=self.refresh,
                                               **rb_options,
                                               ))
            self.buttons[-1].pack(expand=True, anchor=tk.W, fill='x')
        self.buttons[0].select()


    def refresh(self):
        # work out which turn we are using
        current_turn = self.parent.turn_selector.name.get()
        # and save the current variable settings
        global working_params
        self.parent.settings.g_turn_radius.set(working_params[current_turn].arc_radius)
        self.parent.settings.g_turn_delta.set(working_params[current_turn].delta)
        self.parent.settings.g_turn_offset.set(working_params[current_turn].offset)
        self.parent.refresh()



class Settings(tk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(side='left', expand=True, fill='both', padx=5, pady=5)
        self.configure(text='Settings')
        self.parent = parent
        self.row = 0
        # inputs
        self.g_turn_speed = tk.IntVar(value=300)
        self.g_turn_radius = tk.IntVar(value=60)
        self.g_turn_delta = tk.IntVar(value=36)
        self.g_turn_offset = tk.IntVar(value=75)
        self.g_speed_max = tk.IntVar(value=800)
        # outputs
        self.g_turn_omega = tk.StringVar(value='-')
        self.g_turn_alpha = tk.StringVar(value='-')
        self.g_turn_time = tk.StringVar(value='-')
        self.g_turn_speed_max = tk.StringVar(value='-')

        self.add_spin_box('Speed (mm/s):', self.g_turn_speed, 100, 2000, 10)
        self.add_spin_box('Arc Radius (mm):', self.g_turn_radius, 10, 200, 1)
        self.add_spin_box('Delta (mm):', self.g_turn_delta, 5, 200, 1)
        self.add_spin_box('Start Offset (mm):', self.g_turn_offset, 10, 200, 1)

        self.add_separator()
        lb_omega = self.add_output('ppp', self.g_turn_omega)
        lb_alpha = self.add_output('ppp', self.g_turn_alpha)
        lb_time = self.add_output('ppp', self.g_turn_time)
        lb_speed_max = self.add_output('ppp', self.g_turn_speed_max)

    def add_spin_box(self, lbl, var, min_val, max_val, inc):
        lb = ttk.Label(self, text=lbl)
        sb = ttk.Spinbox(self,
                         width=5, justify='right',
                         textvariable=var,
                         from_=min_val, to=max_val, increment=inc,
                         command=self.refresh
                         )
        lb.grid(row=self.row, column=0, sticky=tk.E, padx=5, pady=5)
        sb.grid(row=self.row, column=1, sticky=tk.W, padx=5, pady=5)
        self.row += 1

    def add_output(self, text, var):
        lb = ttk.Label(self,
                       foreground='green',
                       textvariable=var,
                       )
        lb.grid(row=self.row, column=0, columnspan=2, pady=1, padx=5, sticky='w')
        self.row += 1
        return lb

    def add_separator(self):
        separator = ttk.Separator(self, orient='horizontal')
        separator.grid(row=self.row, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        self.row += 1

    def refresh(self):
        # work out which turn we are using
        current_turn = self.parent.turn_selector.name.get()
        # print(self.current_params)
        global working_params
        working_params[current_turn].offset = self.parent.settings.g_turn_offset.get()
        working_params[current_turn].delta = self.parent.settings.g_turn_delta.get()
        working_params[current_turn].arc_radius = self.parent.settings.g_turn_radius.get()
        self.parent.refresh()


class MazeFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(background='black')
        self.turn_name = tk.StringVar(value='----')
        lbl_name = ttk.Label(self,
                             foreground='yellow', background='black',
                             textvariable=self.turn_name,
                             )
        lbl_name.pack(side='top')
        self.maze_view = MazeView(self)
        self.pack(side='top', expand=False, fill='both', padx=5, pady=5)


class MazeView(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, highlightthickness=0, bg='gray5', height=380, width=380)
        self.pack(side='top')
        self.top = 5
        self.left = 5
        self.wall_width = 12
        self.cell_size = 180
        self.draw_maze()

    def origin_x(self):
        return self.left + self.wall_width / 2

    def origin_y(self):
        return self.left + self.wall_width / 2

    def clear(self):
        self.delete('all')
        self.draw_maze()

    def draw_maze(self):
        top = self.top
        left = self.left
        w = self.wall_width

        for x in [0, 1, 2]:
            for y in [0, 1, 2]:
                x1 = left + 180 * x
                y1 = top + 180 * y
                x2 = x1 + 12
                y2 = y1 + 12
                super().create_rectangle(x1, y1, x2, y2, fill='red4', outline='red4')
        for x in [0, 1, 2, 3]:
            for y in [0, 1, 2, 3]:
                x1 = left + 90 * x + w / 2
                y1 = top + 90 * y + w / 2
                x2 = x1 + 90
                y2 = y1 + 90
                super().create_line(x1, y1, x2, y2, fill='red4', dash=(4, 2), )
                super().create_line(x2, y1, x1, y2, fill='red4', dash=(4, 2), )
                super().create_line(x1, y1, x2, y1, fill='red2', dash=(4, 2), )
                super().create_line(x1, y1, x1, y2, fill='red2', dash=(4, 2), )
        x1 = left + w / 2
        x2 = x1 + 2 * 180
        y1 = top + w / 2
        y2 = y1 + 2 * 180
        super().create_line(x2, y1, x2, y2, fill='red2', dash=(4, 2), )
        super().create_line(x1, y2, x2, y2, fill='red2', dash=(4, 2), )

    pass


@dataclass
class Pose:
    '''
    A Pose describes the position (x and y) and orientation (angle)
    of an object.
    The phase is used to describe the current behaviour of the object
    '''

    def __init__(self, x: float = 0, y: float = 0, angle: float = 0, phase: int = 0):
        self.x = x
        self.y = y
        self.angle = angle
        self.phase = phase

    def __repr__(self):
        s = f"{self.x:4d} {self.y:4d} {self.angle:5.1f} {self.phase:1d}"
        return s


###############################################################################
#
# Some transforms on lists of points
###############################################################################

def rotate(points, angle, center):
    ''' Rotate a list of points about a given centre point '''
    angle = math.radians(angle)
    cos_val = math.cos(angle)
    sin_val = math.sin(angle)
    cx, cy = center
    new_points = []
    for x_old, y_old in points:
        x_old -= cx
        y_old -= cy
        x_new = x_old * cos_val - y_old * sin_val
        y_new = x_old * sin_val + y_old * cos_val
        new_points.append([x_new + cx, y_new + cy])
    return new_points


def translate(vertices, delta_x, delta_y):
    ''' translate a list of points by a given delta_x and delta_y '''
    return [[point[0] + delta_x, point[1] + delta_y] for point in vertices]


def scale(vertices, scale_factor):
    ''' translate a list of points by a given delta_x and delta_y '''
    return [[point[0] * scale_factor, point[1]* scale_factor] for point in vertices]

###############################################################################

class Robot:
    def __init__(self, canvas):
        self.canvas = canvas
        self.pose = Pose()
        self.vertices = [[0, 63], [36, 0], [-36, 0], [0, 63]]

    def set_pose(self, pose):
        self.pose = pose

    def draw(self, origin_x, origin_y):
        points = rotate(self.vertices, self.pose.angle, (0, 0))
        points = scale(points, 0.25)
        points = translate(points, self.pose.x + origin_x, self.pose.y + origin_y)
        # self.draw_polygon(self.canvas, points)
        self.canvas.create_polygon(points, outline='white', fill='', width=2)


class TurnProfile:
    def __init__(self, params=None):
        self.params = params
        self.pose = [Pose()]
        self.speed = 300
        self.radius = 60
        self.delta = 36

        pass

    def set_parameters(self, params: TurnParameters):
        self.params = params
        pass

    def set_speed(self, speed):
        self.speed = speed

    def set_radius(self, radius):
        self.radius = radius

    def set_delta(self, delta):
        self.delta = delta

    def calculate(self, loop_interval=0.002):
        angle = self.params.start_angle
        offset = self.params.offset
        robot_x = self.params.pivot_x + offset * math.sin(math.radians(angle))
        robot_y = self.params.pivot_y - offset * math.cos(math.radians(angle))
        self.pose = [Pose(robot_x, robot_y, angle, 0)]
        # get the values from the parameter spinboxes
        # get the initial conditions from the turn parameters
        theta = self.params.start_angle
        # now calculate the working variables
        arc_omega = math.degrees(self.speed / self.radius)
        delta_time = self.delta / self.speed
        alpha = arc_omega / delta_time
        delta_angle = 0.5 * arc_omega * delta_time
        arc_angle = self.params.angle - 2 * delta_angle
        arc_time = arc_angle / arc_omega
        # the three phases of the turn as a function of time
        t1 = delta_time
        t2 = t1 + arc_time
        t3 = t2 + delta_time
        # update the robot output values
        max_available_speed = math.sqrt(5000 * self.radius)
        # run through the turn
        time = 0.0
        omega = 0.0
        mx, my = (self.pose[0].x, self.pose[0].y)
        while time <= t3:
            time += loop_interval
            if time <= t1:
                omega = arc_omega * time / delta_time
                phase = 0
            elif time <= t2:
                omega = arc_omega
                phase = 1
            else:
                omega = arc_omega * (1 - (time - t2) / delta_time)
                phase = 2
            theta = theta + omega * loop_interval
            dx = self.speed * loop_interval * -math.sin(math.radians(theta))
            dy = self.speed * loop_interval * math.cos(math.radians(theta))
            mx += dx
            my += dy
            # print(F'{time:5.3f}  {omega:5.1f} {theta:5.2f} {dx:5.2f} {dy:5.2f} {mx:5.2f} {my:5.2f}')
            self.pose.append(Pose(mx, my, theta, phase))
        # print(F'Finished after {time:5.3f} seconds  at {theta:5.2f} degrees')
        return (arc_omega, alpha, t3, max_available_speed)

    def draw(self,canvas, color = 'yellow'):
        colors = ['green', 'yellow', 'red', 'blue']
        for point in self.pose:
            x = point.x + canvas.origin_x()
            y = point.y + canvas.origin_y()
            color = colors[point.phase]
            canvas.create_oval(x - 1, y - 1, x + 1, y + 1, outline=color)


application = Application("UKMARSBOT Turn Tuner", (420, 720))