import os
import json
import logging
import autoscaling

# Set up logging configuration at the start
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Environment variables
min_capacity = int(os.environ.get("min_capacity"))
max_capacity = int(os.environ.get("max_capacity"))
cluster_identifier = os.environ.get("cluster_identifier")

def handler(event, context):
    if min_capacity > max_capacity:
        logging.critical("The 'min_capacity' cannot be greater than 'max_capacity'.")
        return None

    try:
        docdb = autoscaling.DocumentDB(cluster_identifier, min_capacity, max_capacity)
        replicas_count = docdb.get_replicas_count()

        # Add more replica instances to meet the minimum capacity
        if min_capacity > replicas_count:
            logging.info("Adding more replica instances to meet the minimum capacity...")
            missing_replicas = min_capacity - replicas_count

            while missing_replicas > 0:
                logging.info("Adding replica...")
                docdb.add_replica(ignore_status=True)
                missing_replicas -= 1

            # Ignore the alarm state
            return None

        sns_message = json.loads(event.get('Records')[0].get('Sns').get('Message'))
        new_state_value = sns_message.get('NewStateValue')

        # "In alarm" = scale-out
        if new_state_value == "ALARM":
            logging.info("Scaling out: Adding replica...")
            docdb.add_replica()

        # "OK" = scale-in
        elif new_state_value == "OK":
            logging.info("Scaling in: Removing replica...")
            docdb.remove_replica()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None
