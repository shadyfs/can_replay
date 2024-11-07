# can_replay
Replaying CAN Data from Logs

## Adding Data to Json
The ```parser.py``` file can be run to convert unique data from candump style logs to json format. This will seperate the data out to single frame messages and transport protocol messages in the two json files.

## Replaying Data
The ```can_replay.py``` can replay data to the can bus. It handles both standard messages and transport protocol messages. Currently it does not use BCM as it has to handle transport messages as it has to maintain state space for different types of transport messages and off-loading that to Kernel space will mean we will have to re-configure BCM everytime for each different type of message. Though possible, for a simple use-case its not necessary. The code also does not support Broacast Announcement Messages at the moment and only RTS <--> CTS communication.
