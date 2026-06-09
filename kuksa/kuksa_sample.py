import threading
import time
from kuksa_client.grpc import VSSClient, Datapoint

HOST = "192.168.56.6"
PORT = 55555

stop_event = threading.Event()
client_lock = threading.Lock()


def subscriber_thread(client):
    """Hört auf alle Änderungen unterhalb Vehicle.*"""
    print("[SUB] Subscribed to Vehicle.*")
    for updates in client.subscribe_current_values(["Vehicle"]):
        if stop_event.is_set():
            break
        for path, datapoint in updates.items():
            if datapoint and datapoint.value is not None:
                print(f"[SUB] {path} = {datapoint.value}")

def writeToKuksa(client, path, value):
    client.set_current_values({
        path: Datapoint(value),
    })


def demo_sequence(client):
    # take control over Mini Demo Car (as Cloud)
    print("Take control...")
    writeToKuksa(client, "Vehicle.RequestTakeOver", str([1,120]))
    time.sleep(2)

    # start engine
    print("Start engine...")
    writeToKuksa(client, "Vehicle.Powertrain.StartStop.StartControl", str([1,120]))
    time.sleep(2)

    # accelerate
    print("Accelerating...")
    writeToKuksa(client, "Vehicle.Chassis.Accelerator.PedalPositionControl", str([50,120]))
    time.sleep(2)

    # stop
    print("Stopping...")
    writeToKuksa(client, "Vehicle.Chassis.Accelerator.PedalPositionControl", str([0,120]))
    time.sleep(2)

    # low beam on
    print("Low beam on...")
    writeToKuksa(client,"Vehicle.Body.Lights.ExteriorLightControl", str([1, 5, 120]))
    time.sleep(2)

    # low beam off
    print("Low beam of...")
    writeToKuksa(client, "Vehicle.Body.Lights.ExteriorLightControl", str([0, 5, 120]))
    time.sleep(2)

    # stop engine
    print("Stop engine...")
    writeToKuksa(client, "Vehicle.Powertrain.StartStop.StartControl", str([0,120]))
    time.sleep(2)

    #give back control over Mini Demo Car
    writeToKuksa(client, "Vehicle.RequestTakeOver", str([0,120]))


# def publisher_thread(client, path="Vehicle.Speed", interval=1.0):
#     """Schreibt zyklisch einen inkrementierten Wert auf ein Signal"""
#     print(f"[PUB] Writing to {path} every {interval}s")
#     while not stop_event.is_set():
#         values = [1, 125]
#         with client_lock:
#             client.set_current_values({
#                 path: Datapoint(str(values)),
#             })
#         print(f"[PUB] {path} = {values}")
#         time.sleep(interval)


if __name__ == "__main__":
    with VSSClient(HOST, PORT) as client:
        # listen on everything below Vehicle.*
        sub = threading.Thread(target=subscriber_thread, args=(client,), daemon=True)
        #sub.start()

        demo_sequence(client)

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping...")
            stop_event.set()
            sub.join(timeout=3)
