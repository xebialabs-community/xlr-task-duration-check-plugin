#
# Copyright 2026 XEBIALABS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

# TO-DO:
# - Decide whether or not to fail the task if the task that is being monitored exceeds max duration or has a status of failed
# - Make sure that the polling interval is not necessarily the notification interval, as that might get spammy
#
# Input Variables:
#   taskToCheck         - The task to check duration for
#   maxDuration         - The duration threshold in minutes
#   alertMoment         - When to alert (minutes before maxDuration)
#   pollInterval        - The polling interval in seconds
#   alertFrequency      - Frequency, in minutes, to send alerts after alertMoment has been reached
#   alertFrequencyMax   - Frequency, in minutes, to send alerts after maxDuration has been reached
# Output Variables:
#   totalDuration       - The total duration in minutes

from java.util import Date
import com.xebialabs.xlrelease.domain.status.FlagStatus as FlagStatus

# Variables to use
thisRelease = getCurrentRelease()
thisTask = getCurrentTask()
# Retrieve the tasks with the specified title in the current phase and release
taskBeingCheckedList = taskApi.searchTasksByTitle(taskToCheck, getCurrentPhase().title, thisRelease.id)
# The above provides a list, so we need to get the first item from the list
taskBeingChecked = taskApi.getTask(taskBeingCheckedList[0].id)
# Get the task Status and Start Date
taskStatus = taskBeingChecked.status
taskStartDate = taskBeingChecked.startDate
# Calculate the alert threshold moment
alertThreshold = maxDuration - alertMoment
# Calculate the alert threshold date - Not used currently, but may be useful in future enhancements
alertThresholdDate = Date(taskStartDate.getTime() + (alertThreshold * 60 * 1000))
# Convert poll interval to minutes
pollIntervalMinutes = float(pollInterval) / 60.0
# Get the current task flag status
taskFlagStatus = task.getFlagStatus()

if taskStatus == "IN_PROGRESS":
    now = Date()
    elapsedDuration = ((now.getTime() - taskStartDate.getTime()) / 1000.0 / 60.0)
    if elapsedDuration < alertThreshold:
        # If the task is running, but has not yet reached the alert threshold, reschedule the check, and set status line
        task.setStatusLine("Task *%s* is in progress" % taskToCheck)
        task.schedule("taskDuration/CheckDuration.py",pollInterval)
    elif elapsedDuration >= alertThreshold and elapsedDuration < maxDuration:
        # If the task has exceeded the alert threshold, but not yet the max duration, set flag to attention needed, and print a comment, and reschedule.
        if taskFlagStatus == FlagStatus.OK:
            task.setFlagStatus(FlagStatus.ATTENTION_NEEDED)
            task.setFlagComment("Task %s exceeded alert threshold" % taskToCheck)
            taskApi.updateTask(task)
        # Calculate time since threshold to determine if an alert should be printed
        timeSinceThreshold = elapsedDuration - alertThreshold
        if (timeSinceThreshold % alertFrequency) < pollIntervalMinutes:
            comment = "**ALERT**: Task *%s* has exceeded the alert threshold of %d minutes" % (taskToCheck, alertThreshold)
            taskApi.commentTask(task.id, comment)
        task.setStatusLine("Task *%s* has exceeded the alert threshold" % taskToCheck)
        task.schedule("taskDuration/CheckDuration.py",pollInterval)
    elif elapsedDuration >= maxDuration:
        # If the task has exceeded the max duration, set flag to at risk, print a comment, and reschedule.
        if taskFlagStatus != FlagStatus.AT_RISK:
            task.setFlagStatus(FlagStatus.AT_RISK)
            task.setFlagComment("Task %s exceeded maximum duration" % taskToCheck)
            taskApi.updateTask(task)
        timeSinceMax = elapsedDuration - maxDuration
        # Check if we are currently at a frequency interval
        if (timeSinceMax % alertFrequencyMax) < pollIntervalMinutes:
            comment = "**ALERT**: Task *%s* has exceeded the maximum duration of %d minutes" % (taskToCheck, maxDuration)
            taskApi.commentTask(task.id, comment)
        task.setStatusLine("Task *%s* has exceeded the maximum duration" % taskToCheck)
        task.schedule("taskDuration/CheckDuration.py",pollInterval)
elif taskStatus == "SKIPPED":
    taskEndDate = taskBeingChecked.endDate
    totalDurationCalc = (taskEndDate.getTime() - taskStartDate.getTime()) / 1000.0 / 60.0
    totalDuration = int(round(totalDurationCalc))
    task.setStatusLine("Task *%s* was skipped" % taskToCheck)
    comment = "Task *%s* was skipped after %d minutes" % (taskToCheck, totalDuration)
    taskApi.commentTask(task.id, comment)
elif taskStatus == "FAILED":
    comment = "Task *%s* has failed" % (taskToCheck)
    taskApi.commentTask(task.id, comment)
    taskApi.abortTask(thisTask.getId(), "Task %s has failed" % taskToCheck)
elif taskStatus == "COMPLETED":
    taskEndDate = taskBeingChecked.endDate
    totalDurationCalc = (taskEndDate.getTime() - taskStartDate.getTime()) / 1000.0 / 60.0
    totalDuration = int(round(totalDurationCalc))
    comment = "Task *%s* completed in %d minutes" % (taskToCheck, totalDuration)
    taskApi.commentTask(task.id, comment)
    task.setStatusLine("Task *%s* completed in %s minutes" % (taskToCheck, totalDuration))
    if totalDuration > maxDuration:
        comment = "Task *%s* exceeded the maximum duration of %d minutes" % (taskToCheck, maxDuration)
        taskApi.commentTask(task.id, comment)
    else:
        comment = "Task *%s* completed within the maximum duration of %d minutes" % (taskToCheck, maxDuration)
        taskApi.commentTask(task.id, comment)