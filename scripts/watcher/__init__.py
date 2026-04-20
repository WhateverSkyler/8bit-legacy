"""8-Bit Legacy content-drop watcher + buffer scheduler.

Runs inside the pipeline container on TrueNAS. See drop_watcher.py for the
main polling loop; buffer_scheduler.py (coming) handles re-posting from the
clip archive when the scheduled queue runs low.
"""
