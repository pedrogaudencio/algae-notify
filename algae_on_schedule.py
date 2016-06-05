from algae import AlgaeNotify
import json
import sys


if __name__ == "__main__":
    """Run as a cron job."""
    with open('config.json') as f:
        config = json.load(f)
        algae = AlgaeNotify(config)
        algae.photosynthesis()
        failures = algae.check_range()
        algae.log(failures, send=True)
        sys.exit()
