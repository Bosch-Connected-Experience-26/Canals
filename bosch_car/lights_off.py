import time

from kuksa_client.grpc import Datapoint, VSSClient

HOST = "192.168.56.6"
PORT = 55555
CLIENT_ID = 120

with VSSClient(HOST, PORT) as client:
    print("Connected to KUKSA")

    # Take control of the Mini Demo Car
    client.set_current_values(
        {"Vehicle.RequestTakeOver": Datapoint(str([1, CLIENT_ID]))}
    )

    print("TakeOver requested")
    time.sleep(2)

    # Turn LOW BEAM OFF
    client.set_current_values(
        {"Vehicle.Body.Lights.ExteriorLightControl": Datapoint(str([0, 5, CLIENT_ID]))}
    )

    print("Low beam OFF command sent")
    time.sleep(2)

    # Turn ALL LIGHTS OFF
    client.set_current_values(
        {"Vehicle.Body.Lights.ExteriorLightControl": Datapoint(str([0, 0, CLIENT_ID]))}
    )

    print("All lights OFF command sent")
