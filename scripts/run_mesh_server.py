from python.mesh_server import create_mesh_server


if __name__ == "__main__":
    server = create_mesh_server()
    print("Offline mesh API listening on http://0.0.0.0:8765")
    print("Endpoints: GET /health, GET /incidents, POST /incidents")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
