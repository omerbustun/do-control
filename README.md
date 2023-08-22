do-control
==========

Mass control and management of DigitalOcean droplets using Python, Django, and the DO Python library.

Features
--------

*   Built with Python and Django for robust web application functionality.
*   Utilizes the [Tabler](https://github.com/tabler/tabler) admin template for a clean and intuitive user interface.
*   Offers a unified platform for managing multiple DigitalOcean droplets.

Setup
-----

1.  Clone the repository.
2.  Navigate to the project directory.
3.  Create an `.env` file in the root of the project and set your Django secret key like this:
    
    ```
    SECRET_KEY=your_secret_key_here
    ```
    
4.  Install the required dependencies using:
    ```
    pip install -r requirements.txt
    ```
    
5.  Run the project using Django's `runserver` command.
    ```
    python manage.py runserver
    ```