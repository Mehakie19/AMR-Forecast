PYTHON ?= python
export PYTHONPATH := src

.PHONY: eda features train final-test ui-data test install api streamlit frontend build-frontend

install:
	$(PYTHON) -m pip install -r requirements.txt

eda:
	$(PYTHON) scripts/run_eda.py

features:
	$(PYTHON) scripts/run_features.py

train:
	$(PYTHON) scripts/run_train.py

final-test:
	$(PYTHON) scripts/run_final_test.py

ui-data:
	$(PYTHON) scripts/run_ui_data.py

test:
	$(PYTHON) -m pytest tests/ -q

api:
	uvicorn api.main:app --reload --host 127.0.0.1 --port 8001

frontend:
	npm run dev --prefix frontend

build-frontend:
	npm run build --prefix frontend

streamlit:
	streamlit run app/streamlit_app.py
