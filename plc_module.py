import plc_controller
import time


""""plc has multiple communication protocols and hardware interfaces
hardware interfaces include the following
tcp
rs232
rs485
etc

communication protocols include the following
Modbus (TCP,RTU,ASCII)
SLMP
Profinet
etc

this module is built assuming we are going with Modbus TCP for now
"""

class PLC():
    
    plc = plc_controller.ModbusController()
    ip = "192.168.1.50"
    plc.connect(ip,mode='TCP')

    def __init__(self):
        # self.plc = plc_controller.ModbusController()
        # self.ip = "192.168.1.50"
        # self.plc.connect(self.ip,mode='TCP')
        ...


    # def check_connection(self):
    #     for i in range(10):
    #         status = self.plc.connect(self.ip,mode='TCP')
    #         if status:
    #             return True
    #         time.sleep(2)
    #     return False
