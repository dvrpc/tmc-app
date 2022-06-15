# tmc-app

`Flask` front end for the [`tmc_summarizer`](https://github.com/dvrpc/tmc-summarizer)

## Live Demo

Here: [http://167.172.146.34](http://167.172.146.34)

![image info](./static/assets/images/app_screenshot.png)

## Deployment

This app is running on the cheapest DigitalOcean droplet available, at $5/month.

Server was set up following [https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04)

## Development Environment Setup

Create/activate an environment:

```bash
(base) $ conda create --name tmc_env python=3.9
(tmc_env) $ conda activate tmc_env
```

Install the requirements:

```bash
(tmc_env) $ conda install --file requirements.txt
```

Create the `.env` file:

```bash
(tmc_env) $ touch .env
```

Open the `.env` file and set the `GMAPS_API_KEY`:

```bash
GMAPS_API_KEY=abc123xyz
```

## Run the app

```bash
(tmc_env) $ python tmc_app.py
```
