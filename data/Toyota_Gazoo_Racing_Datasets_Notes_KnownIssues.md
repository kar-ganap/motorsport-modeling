Notes and known issues about telemetry and lap start/end/time files
meta_time: The time the message was received.

timestamp: The time on the electronic control unit (ECU) of the vehicle. The time on the ECU may not be accurate.

Vehicle identification: Example: For GR86-004-78, the chassis number is 004 and the car number is 78 (the sticker on the side of the car). If the car number is 000, it hasn't been assigned to the ECU yet. You can still uniquely identify a vehicle by its chassis number though. In a later race, you might see the car number updated.

lap: Sometimes the lap count is lost or erroneously reported (often as lap #32768). The time values should still be accurate, and the lap may be determined by it.

Vehicle Telemetry Parameters
Speed & Drivetrain
Speed	Actual vehicle speed (km/h)
Gear	Current gear selection
nmot	Engine RPM
Throttle & Braking
ath	Throttle blade position (0% = fully closed, 100% = wide open)
aps	Accelerator pedal position (0% = no acceleration, 100% = fully pressed)
pbrake_f	Front brake pressure (bar)
pbrake_r	Rear brake pressure (bar)
Acceleration & Steering
accx_can	Forward/backward acceleration in G's (positive = accelerating, negative = braking)
accy_can	Lateral acceleration in G's (positive = left turn, negative = right turn)
Steering_Angle	Steering wheel angle in degrees (0 = straight, negative = counterclockwise, positive = clockwise)
Position & Lap Data
VBOX_Long_Minutes	GPS longitude (degrees)
VBOX_Lat_Min	GPS latitude (degrees)
Laptrigger_lapdist_dls	Distance from start/finish line (meters)
