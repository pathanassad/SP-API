import io
import requests
import networkx as nx
import matplotlib.pyplot as plt
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import math

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Request model for the API
class GraphRequest(BaseModel):
    api_url: str

# Function to fetch data from the API endpoint
def fetch_data(api_url):
    response = requests.get(api_url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from the API.")
    data = response.json()["data"]
    return data

# Function to parse response JSON to extract points and coordinates
def parse_data(data):
    points_coordinates = {entry["points"]: eval(entry["coordinates"]) for entry in data}
    return points_coordinates

# Function to create a layout based on the coordinates
def create_layout(points_coordinates):
    layout = {}
    for point, coordinates in points_coordinates.items():
        layout[point] = coordinates
    return layout

# Function to generate stop points (S points)
def generate_stop_points(layout):
    stop_points = []

    # Extract the coordinates of the Z points
    z_points = [point for point in layout.keys() if point.startswith("Z")]
    z_coords = [layout[point] for point in z_points]

    # Iterate through each pair of Z points to generate S points
    for i in range(len(z_coords)):
        x1, y1 = z_coords[i]
        for j in range(i + 1, len(z_coords)):
            x2, y2 = z_coords[j]

            # Calculate the distance between Z points
            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            # Generate S points along the edge if the distance is greater than 1 meter
            if distance > 1:
                # Check if the edge is horizontal or vertical
                if x1 == x2:  # Vertical edge
                    num_intervals = int(distance)
                    y_step = (y2 - y1) / num_intervals
                    for k in range(1, num_intervals):
                        x = x1
                        y = y1 + k * y_step
                        # Create S point if there is no node at this position
                        if not any(abs(node[0] - x) < 0.01 and abs(node[1] - y) < 0.01 for node in layout.values()):
                            s_point = f"S{int(x)}{int(y)}"
                            stop_points.append(s_point)
                            layout[s_point] = (x, y)
                elif y1 == y2:  # Horizontal edge
                    num_intervals = int(distance)
                    x_step = (x2 - x1) / num_intervals
                    for k in range(1, num_intervals):
                        x = x1 + k * x_step
                        y = y1
                        # Create S point if there is no node at this position
                        if not any(abs(node[0] - x) < 0.01 and abs(node[1] - y) < 0.01 for node in layout.values()):
                            s_point = f"S{int(x)}{int(y)}"
                            stop_points.append(s_point)
                            layout[s_point] = (x, y)

    return stop_points

# Function to create the graph and plot it
def create_graph(api_url):
    data = fetch_data(api_url)
    points_coordinates = parse_data(data)
    layout = create_layout(points_coordinates)
    G = nx.Graph()

    stop_points = generate_stop_points(layout)

    for point, coordinates in layout.items():
        G.add_node(point, pos=coordinates)

    for s_point in stop_points:
        G.add_node(s_point, pos=layout[s_point])

    for point1, coord1 in layout.items():
        if not point1.startswith("O"):
            for point2, coord2 in layout.items():
                if point1 != point2 and (not point1.startswith(("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"))) and (not point2.startswith(("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"))) and (not point2.startswith("O")):
                    distance = math.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)
                    if distance < 1.1:
                        G.add_edge(point1, point2)

    for s_point in stop_points:
        s_x, s_y = layout[s_point]
        for point, coordinates in layout.items():
            x, y = coordinates
            if (point.startswith("A") or point.startswith("B") or point.startswith("C") or point.startswith("D") or point.startswith("E") or point.startswith("F") or point.startswith("G") or point.startswith("H") or point.startswith("I") or point.startswith("J") or point.startswith("K") or point.startswith("L")) and x == s_x and abs(y - s_y) == 1:
                G.add_edge(point, s_point)

    return G, layout

@app.post("/graph")
def get_graph(request: GraphRequest):
    G, layout = create_graph(request.api_url)

    plt.figure(figsize=(9, 8))
    node_colors = ['#FFFC9B' if node.startswith('Z') or node.startswith('S') or node.startswith('O') else '#FFF3C7' for node in G.nodes()]
    node_shapes = ['s' if node.startswith('A') or node.startswith('B') or node.startswith("C") or node.startswith("D") or node.startswith("E") or node.startswith("F") or node.startswith("G") or  node.startswith("H") or node.startswith("I") or node.startswith("J") or node.startswith("K") or node.startswith("L") else 'o' for node in G.nodes()]

    for node, color, shape in zip(G.nodes(), node_colors, node_shapes):
        if shape == 's':
            nx.draw_networkx_nodes(G, layout, nodelist=[node], node_size=200, node_color=color, node_shape='s', linewidths=2)
        else:
            nx.draw_networkx_nodes(G, layout, nodelist=[node], node_size=700, node_color=color, node_shape='o', linewidths=2)

    nx.draw_networkx_labels(G, layout, font_size=10, font_weight='bold')
    plt.axis("off")

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return StreamingResponse(buf, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
