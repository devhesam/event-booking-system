install:
	pip install --upgrade pip
	pip install -r requirements.txt

migrate:
	python manage.py migrate

server:
	python manage.py runserver

check:
	python3 manage.py check

test:
	pytest -v

test-bookings:
	pytest events/tests/test_booking.py -v

worker:
	celery -A config worker -l info

beat:
	celery -A config beat -l info

shell:
	python manage.py shell

makemigrations:
	python manage.py makemigrations

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -type d -exec rm -rf {} +