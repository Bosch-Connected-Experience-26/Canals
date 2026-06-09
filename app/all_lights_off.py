import time

from kuksa_client.grpc import Datapoint, VSSClient

HOST = "192.168.56.6"
PORT = 55555
CLIENT_ID = 120

with VSSClient(HOST, PORT) as client:
    client.set_current_values(
        {"Vehicle.RequestTakeOver": Datapoint(str([1, CLIENT_ID]))}
    )

    time.sleep(1)

    client.set_current_values(
        {"Vehicle.Body.Lights.ExteriorLightControl": Datapoint(str([0, 0, CLIENT_ID]))}
    )

    print("All Lights OFF")
