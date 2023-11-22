import urx

class Cobot:
    def __init__(self,ip):
        self.robot_controller = urx.Robot(ip)
        self.default_acc = 1
        self.default_vel = 1

    def get_position(self):
        data = self.robot_controller.getj(wait=True)
        data1 = {'move_type':'j','a': self.default_acc,'v': self.default_vel}

        for j in range(len(data)):
            data1['j'+str(j+1)] = data[j]
        return data1

    def set_position(self,pos):
        if pos['move_type'] == 'j':
            self.robot_controller.movej([pos['j1'], pos['j2'], pos['j3'], pos['j4'], pos['j5'], pos['j6']],pos['a'],pos['v'],wait=False)
            while self.robot_controller.is_program_running():
                    print('Robot Started Moving')
            print("Robot Stopped")
            # while 1:

            #     if self.robot_controller.is_program_running():
            #         # print(r.getj(wait=True))
            #         # time.sleep(0.1)
            #         pass
            #     else:
            #         print('Robot Stopped')
            #         # print(r.getj(wait=True))
            #         # time.sleep(1)
            #         break
