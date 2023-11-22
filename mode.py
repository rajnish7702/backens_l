from common import *
# from multiprocessing import Process, Pipe, set_start_method
# import torch.multiprocessing as mp
mode = list(data.keys())[0]
print("In mode.py")

# try:
#     mp.set_start_method('spawn')
# except RuntimeError:
#     pass

if mode == "data_capture":
    from data_capture import trigger_listen
    trigger_listen()

elif mode == "inference":
    from main import start_server
    start_server()
    # from camera_service import start_stream_server
    # from model import load_model

    # # parent_conn, child_conn = Pipe()
    # if __name__ == "__main__":
    #     mp.set_start_method('fork', force=True)
    # p2 = mp.Process(target=start_stream_server)
    # p2.start()

    # p1 = mp.Process(target=start_server)
    # p1.start()

    # p3 = mp.Process(target=load_model)
    # p3.start()

