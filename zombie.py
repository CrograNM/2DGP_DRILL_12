from pico2d import *

import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import play_mode


# zombie Run Speed
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# zombie Action Speed
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')


    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0      # radian 값으로 방향을 표시
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0
        self.tx, self.ty = 0, 0
        self.build_behavior_tree()
        self.patrol_locations = [(43, 274), (1118, 274), (1050, 494), (575, 804), (235, 991), (575, 804), (1050, 494),
                                 (1118, 274)]
        self.loc_no = 0

    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50


    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        # fill here
        self.bt.run()

    def draw(self):
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)
        self.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        draw_rectangle(*self.get_bb())

    def handle_event(self, event):
        pass

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1


    def set_target_location(self, x=None, y=None):
        if not x or not y:
            raise ValueError('Location should be given')
        self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS

    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distance2 < (PIXEL_PER_METER * r) ** 2

    def move_slightly_to(self, tx, ty):
        self.dir = math.atan2(ty - self.y, tx - self.x)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

    def move_to(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(self.tx, self.ty)
        if self.distance_less_than(self.tx, self.ty, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def set_random_location(self):
        self.tx, self.ty = random.randint(100, 1280 - 100), random.randint(100, 1024 - 100)
        return BehaviorTree.SUCCESS

    def is_boy_nearby(self, distance):
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, distance):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def move_to_boy(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(play_mode.boy.x, play_mode.boy.y)
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def away_from_boy(self, r=7):
        self.state = 'Walk'
        dx = play_mode.boy.x - self.x
        dy = play_mode.boy.y - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5  # 소년과의 현재 거리 계산

        # 거리가 r 이상이 되도록 이동 방향 설정
        if distance < r:
            scale = r / distance if distance != 0 else 1  # 거리 비율로 스케일 계산
            dx *= scale
            dy *= scale

        res_x = self.x - dx  # 반대 방향으로 이동
        res_y = self.y - dy

        # 경계값 클램핑
        res_x = max(0, min(1280, res_x))
        res_y = max(0, min(1024, res_y))

        self.move_slightly_to(res_x, res_y)  # 소년과 정반대 방향으로 이동

        if self.distance_less_than(res_x, res_y, self.x, self.y, r):
            self.set_random_location()
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def get_patrol_location(self):
        self.tx, self.ty = self.patrol_locations[self.loc_no]
        self.loc_no = (self.loc_no + 1) % len(self.patrol_locations)
        return BehaviorTree.SUCCESS

    def check_ball_count(self):
        if self.ball_count < play_mode.boy.ball_count:
            return BehaviorTree.FAIL
        else:
            return BehaviorTree.SUCCESS

    def build_behavior_tree(self):
        a1 = Action('Set target location', self.set_target_location, 1000, 1000)
        a2 = Action('Move to', self.move_to)
        root = move_to_target_location = Sequence('Move to target location', a1, a2)

        a3 = Action('Set random location', self.set_random_location)
        root = wander = Sequence('Wander', a3, a2)

        c1 = Condition('소년과 공의 개수 비교', self.check_ball_count)
        a4 = Action('소년 위치로 이동', self.move_to_boy)
        root = chase = Sequence('소년추적', c1, a4)

        a5 = Action('소년 반대 방향 이동', self.away_from_boy)
        root = flee = Sequence('도망치기',  a5)

        root = chase_or_flee = Selector('추적 or 도망', chase, flee)
        c2 = Condition('소년이 근처에 있는가?', self.is_boy_nearby, 7)
        root = check_chace_flee = Sequence('근처면 (추적 or 도망) 확인', c2, chase_or_flee)
        root = chase_flee_wander = Selector('추적 or 도망 or 배회', check_chace_flee, wander)

        self.bt = BehaviorTree(root)
