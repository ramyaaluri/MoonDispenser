from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from flask_cors import CORS
import logging


# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/') # Database and collection
db = client['pad_dispenser_db']
machines_collection = db['machines']

# Route to display a simple interactive home page
@app.route('/', methods=['GET'])
def home():
    return '''
        <h1>Welcome to the Pad Dispenser Backend</h1>
        <p>Use the buttons below to interact with the API:</p>
        <button onclick="window.location.href='/list_machines';">List Machines</button>
        <form action="/register_machine" method="post" style="margin-top:10px;">
            <label>Machine ID: <input type="text" name="machine_id" required></label><br>
            <label>Location: <input type="text" name="location" required></label><br>
            <label>Pad Count: <input type="number" name="pad_count" value="0"></label><br>
            <button type="submit">Register Machine</button>
        </form>
        <form action="/update_pad_count" method="post" style="margin-top:10px;">
            <label>Machine ID: <input type="text" name="machine_id" required></label><br>
            <label>New Pad Count: <input type="number" name="pad_count" required></label><br>
            <button type="submit">Update Pad Count</button>
        </form>
    '''

@app.route('/api/machines', methods=['POST'])
def add_machine():
    data = request.get_json()
    if not data or 'name' not in data or 'location' not in data or 'padCount' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    # Proceed with adding the machine to the database
    return jsonify({'message': 'Machine added successfully'}), 201

@app.route('/register_machine', methods=['POST'])
def register_machine():
    data = request.get_json()
    logging.debug(f"Received data: {data}")  # Log the received data

    machine_id = data.get('machine_id')
    building_name = data.get('building_name')
    floor_number = data.get('floor_number')
    sqft = data.get('sqft')
    area_id = data.get('area_id')
    pad_count = data.get('pad_count', 0)

    if not building_name or not area_id:
        return jsonify({"error": "Building name and Area ID are required."}), 400

    # Log to ensure data is correct
    logging.debug(f"Inserting machine: {machine_id}, {building_name}, {floor_number}, {sqft}, {area_id}, {pad_count}")

    # Add machine to the database
    if not machine_id:
        # You can handle the case where machine_id is provided
        pass
    else:
        machine = {
            "machine_id": machine_id,  # Include machine_id
            "building_name": building_name,
            "floor_number": floor_number if floor_number else None,
            "sqft": float(sqft) if sqft else None,
            "area_id": area_id if area_id else None,
            "pad_count": int(pad_count),
            "last_updated": datetime.utcnow()
        }

        # Check if the insertion is successful
        result = machines_collection.insert_one(machine)
        logging.debug(f"Insert result: {result.inserted_id}")  # Log the inserted ID to confirm the insertion

    return jsonify({"message": "Machine registered successfully!"}), 201


# Route to update pad count
@app.route('/update_pad_count', methods=['POST'])
def update_pad_count():
    machine_id = request.form.get('machine_id')
    building_name = request.form.get('building_name')
    pad_count = request.form.get('pad_count')

    if not machine_id or building_name or pad_count is None:
        return jsonify({"error": "Machine ID and pad count are required."}), 400

    # Update pad count in the database
    result = machines_collection.update_one(
        {"machine_id": machine_id},
        {"$set": {"pad_count": int(pad_count), "last_updated": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Machine not found."}), 404

    return jsonify({"message": "Pad count updated successfully!"}), 200


@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    try:
        data = request.get_json()

        # Insert data into the database
        insert_machines_data(data)

        return jsonify({"message": "Data uploaded successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to get machine status
@app.route('/machine_status', methods=['GET'])
def machine_status():
    machine_id = request.args.get('machine_id')

    if not machine_id:
        return jsonify({"error": "Machine ID is required."}), 400

    # Retrieve machine data from the database
    machine = machines_collection.find_one({"machine_id": machine_id}, {"_id": 0})

    if not machine:
        return jsonify({"error": "Machine not found."}), 404

    return jsonify(machine), 200

@app.route("/list_machines", methods=["GET"])
def list_machines():
    try:
        machines = list(machines_collection.find({}, {"_id": 0}))
        if not machines:
            return "<h2>No machines registered yet!</h2><button onclick=\"window.location.href='/';\">Go Back</button>"

        response = "<h2>List of Machines:</h2><ul>"
        for machine in machines:
            response += (
                f"<li>"
                f"Building: {machine.get('building_name', 'N/A')} - "
                f"Floor: {machine.get('floor_number', 'N/A')} - "
                f"Sqft: {machine.get('sqft', 'N/A')} - "
                f"Area ID: {machine.get('area_id', 'N/A')} - "
                f"Pad Count: {machine.get('pad_count', 'N/A')}"
                f"</li>"
            )
        response += '</ul><button onclick="window.location.href=\'/\';">Go Back</button>'
        return response
    except Exception as e:
        return f"<h2>Error: {str(e)}</h2>"


@app.route('/list_machines_json', methods=['GET'])
def list_machines_json():
    try:
        # Use MongoDB aggregation to group by building name
        pipeline = [
            {
                "$group": {
                    "_id": "$building_name",  # Group by building name
                    "machines": {
                        "$push": {
                            "machine_id": "$machine_id",
                            "floor_number": "$floor_number",
                            "sqft": "$sqft",
                            "area_id": "$area_id",
                            "pad_count": "$pad_count"
                        }
                    }
                }
            },
            {"$sort": {"_id": 1}}  # Sort the groups by building name
        ]

        machines = list(machines_collection.aggregate(pipeline))

        return jsonify(machines)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to delete a machine (for management purposes)
@app.route('/delete_machine', methods=['DELETE'])
def delete_machine():
    data = request.json
    machine_id = data.get('machine_id')

    if not machine_id:
        return jsonify({"error": "Machine ID is required."}), 400

    result = machines_collection.delete_one({"machine_id": machine_id})

    if result.deleted_count == 0:
        return jsonify({"error": "Machine not found."}), 404

    return jsonify({"message": "Machine deleted successfully!"}), 200

def insert_machines_data(data):
    for row in data:
        machine_id = row.get("Machine ID")
        building_name = row.get("Building Name")
        floor_number = row.get("Floor Number")
        sqft = row.get("Actual SF")
        area_id = row.get("AreaID")
        pad_count = row.get("Pad Count")

        if not building_name:
            continue  # Skip rows with missing mandatory fields

        machine = {
            "machine_id": machine_id,
            "building_name": building_name,
            "floor_number": int(floor_number) if floor_number else None,
            "sqft": float(sqft) if sqft else None,
            "area_id": area_id,
            "pad_count": int(pad_count) if pad_count else 0,
            "last_updated": datetime.utcnow()
        }

        machines_collection.insert_one(machine)

# @app.route('/list_machines_json', methods=['GET'])
# def list_machines_json():
#     machines = list(machines_collection.find({}, {"_id": 0}))
#     return jsonify(machines)
#

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
