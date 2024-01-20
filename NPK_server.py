from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
from flask_cors import CORS
import csv
from datetime import datetime
import util

val1 = 0.2
val2 = 10
val3 = 0.5
id = 20
timestamp = '2023-12-08 12:45:02' #datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

util_path = "util.py"
app = Flask(__name__, static_url_path='/static')

# app = Flask(__name__)
CORS(app)

socketio = SocketIO(app)

# CSV file path
csv_file_path = 'NPK_database.csv'
fieldnames = ['TIMESTAMP', 'N_VALUE', 'P_VALUE', 'K_VALUE', 'FERTILIZER', 'id']

# Helper function to read all records from the CSV file
# Helper function to read all records from the CSV file
def read_records():
    records = []
    with open(csv_file_path, 'r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            records.append({
                'TIMESTAMP': row['TIMESTAMP'],
                'N_VALUE': row['N_VALUE'],
                'P_VALUE': row['P_VALUE'],
                'K_VALUE': row['K_VALUE'],
                'FERTILIZER': row['FERTILIZER'],
                'id': row['id'],
            })
    return records


# Helper function to write records to the CSV file
def write_records(records):
    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            try:
            # Ensure the timestamp is in the correct format (string)
            # timestamp = record['timestamp']
            # Write the record to the CSV file
                writer.writerow({
                    'TIMESTAMP': record['TIMESTAMP'],
                    'N_VALUE': record['N_VALUE'],
                    'P_VALUE': record['P_VALUE'],
                    'K_VALUE': record['K_VALUE'],
                    'FERTILIZER': record['FERTILIZER'],
                    'id': record['id']
                })
            except KeyError as e:
                print(f"KeyError: {e} not found in record. Skipping this record.")
                print("Record:", record)

# Background thread to send data to the frontend
def background_thread():
    while True:
        socketio.sleep(5)  # Update every 5 seconds
        records = read_records()
        socketio.emit('update_data', {'data': records}, namespace='/test')

@app.route('/')
def index():
    get_records()
    return render_template('index_realtime.html')

@app.route('/send_data', methods=['POST'])
def receive_dat():
    global val1, val2, val3, timestamp, id, data1, data2, data3, result
    received_data = request.get_json()

    # Read existing records
    records = read_records()

    if 'N_value' in received_data and 'P_value' in received_data and 'K_value' in received_data:
        val1 = received_data['N_value']
        val2 = received_data['P_value']
        val3 = received_data['K_value']
        id = len(records) + 1

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #get result using val1, val2 and val3
        predict_user_input()

        print(f"Received gas1: {val1}, val2: {val2}, val3: {val3}")

        # Append the received data to the CSV file
        new_record = {
            'TIMESTAMP': timestamp,
            'N_VALUE': val1,
            'P_VALUE': val2,
            'K_VALUE': val3,
            'FERTILIZER': result,
            'id': len(records) + 1,
        }
        records.append(new_record)

        # Write the updated records to the CSV file
        write_records(records)

        return "Data received and saved successfully", 200
    else:
        return "Invalid data format", 400

# Route to receive and process data via websocket
@socketio.on('esp32_data', namespace='/test')
def receive_data(message):
    global val1, val2, val3, timestamp, id, data1, data2, data3, result

    try:
        val1 = float(message.get('N_value'))
        val2 = float(message.get('P_value'))
        val3 = float(message.get('K_value'))

        # Additional processing logic
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"Received gas1: {val1}, val2: {val2}, val3: {val3}")

        predict_user_input()

        # Append the received data to the CSV file
        new_record = {
            'TIMESTAMP': timestamp,
            'N_value': val1,
            'P_value': val2,
            'K_value': val3,
            'FERTILIZER': result,
            'id': len(read_records()) + 1,
        }

        # Read existing records
        records = read_records()
        records.append(new_record)

        # Write the updated records to the CSV file
        write_records(records)

        # Broadcast an update to connected clients
        socketio.emit('update_data', {'data': records}, namespace='/test')
    except ValueError as e:
        print(f"Error processing data: {e}")


@socketio.on('connect', namespace='/test')
def test_connect():
    print("Client connected")
    socketio.emit('update_data', {'data': read_records()}, namespace='/test')

@app.route('/predict', methods=['GET'])
def predict_user_input():
    try:
        global val1, val2, val3, result
        # Use the received values or default values if not received
        input1 = val1
        input2 = val2
        input3 = val3

        # Call the utility function to make predictions
        result = util.predict_user_input(input1, input2, input3)
        # Construct the response
        response = jsonify({
            'fertilizer': result
        })
        return response

    except ValueError as e:
        return jsonify({'error': str(e)})

@app.route('/download_csv')
def download_csv():
    #Sends the database to the front end for download
    return send_file(csv_file_path, as_attachment=True)

@app.route('/download_dataset')
def download_dataset():
    #Sends the database to the front end for download
    return send_file('NPK_DATASET.csv', as_attachment=True)

# Route to get all records
@app.route('/records', methods=['GET'])
def get_records():
    records = read_records()
    return jsonify(records)

# @app.route('/download_csv')
# def download_csv():
#     return send_file('Nalasha_database.csv', as_attachment=True)

# New route to get real-time data
@app.route('/get_real_time_data', methods=['GET'])
def get_real_time_data():
    records = read_records()
    return jsonify({'data': records})


@app.route('/delete_all_data', methods=['POST'])
def delete_all_data():
    try:
        # Delete all records from the CSV file
        write_records([])

        # Emit an update to connected clients after data deletion
        socketio.emit('update_data', {'data': []}, namespace='/test')

        return jsonify({'message': 'All data deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    socketio.start_background_task(target=background_thread)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # Set debug to False



# Example usage:

# GET all records: GET http://localhost:5000/records
# POST a new record: POST http://localhost:5000/records with JSON payload {"name": "John Doe", "age": 25}
# PUT (update) a record by ID: PUT http://localhost:5000/records/1 with JSON payload {"name": "Updated Name", "age": 30}
# DELETE a record by ID: DELETE http://localhost:5000/records/1


# # Route to create a new record
# @app.route('/records', methods=['POST'])
# def create_record():
#     data = request.json
#     records = read_records()
#     data['id'] = len(records) + 1
#     records.append(data)
#     write_records(records)
#     return jsonify({'message': 'Record created successfully'}), 201


# # Route to update a record by ID
# @app.route('/records/<int:record_id>', methods=['PUT'])
# def update_record(record_id):
#     data = request.json
#     records = read_records()
#     for record in records:
#         if record['id'] == record_id:
#             record.update(data)
#             write_records(records)
#             return jsonify({'message': 'Record updated successfully'})
#     return jsonify({'error': 'Record not found'}), 404

# # Route to delete a record by ID
# @app.route('/records/<int:record_id>', methods=['DELETE'])
# def delete_record(record_id):
#     records = read_records()
#     new_records = [record for record in records if record['id'] != record_id]
#     if len(new_records) < len(records):
#         write_records(new_records)
#         return jsonify({'message': 'Record deleted successfully'})
#     return jsonify({'error': 'Record not found'}), 404
