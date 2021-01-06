#!/bin/sh
gunicorn --chdir app app:app -w 1 --threads 2 -b :8000