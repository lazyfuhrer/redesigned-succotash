Create  virtual environment
> python3 -m venv venv

Install packages 
> pip install -r requirements.txt
 
Install Postgres & create a db 

Create environment file `.env` file

example
>DATABASE="name=xxxx,user=xxxx,password=xxxx,port=5432,host=localhost"
>SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 
Run application

Export Fixtures on first time
> python manage.py dumpdata clinic.Clinic --output=clinics_data.json 
> 
> python manage.py dumpdata clinic.ClinicTiming --output=clinics_timings_data.json
> 
> python manage.py dumpdata appointment.Category --output=appointment_category_data.json
> 
> python manage.py dumpdata appointment.Procedure --output=appointment_procedure_data.json
> 
> python manage.py dumpdata appointment.Tax --output=appointment_tax_data.json

Import Fixtures
> python manage.py loaddata fuelapp/fixtures/appointment_tax_data.json
> 
Run Celery
> celery -A fuelapp worker -l info
> celery -A fuelapp beat -l info

