from Do_not_deploy.query_outgoing_queue import app
app.run(debug=True, host="0.0.0.0", port=5003)
