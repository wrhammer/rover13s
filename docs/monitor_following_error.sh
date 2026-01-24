#!/bin/bash
# Monitor Joint 1 following error to see if it's building up over time
# Run this before starting a job, let it run for 20+ minutes

echo "Time,Following_Error,Position_Cmd,Position_Fb,PID_Output,PID_Integral"
while true; do
    TIME=$(date +%s)
    FERROR=$(halcmd getp joint.1.f-error)
    CMD=$(halcmd getp joint.1.motor-pos-cmd)
    FB=$(halcmd getp joint.1.motor-pos-fb)
    PID_OUT=$(halcmd getp pid.y.output)
    PID_INT=$(halcmd getp pid.y.integral)
    echo "$TIME,$FERROR,$CMD,$FB,$PID_OUT,$PID_INT"
    sleep 1
done

