# Selenium Tricks

### How to build 
```bash
docker-compose up
```
### Rebuild removing cache
```bash
docker-compose build --no-cache && docker-compose up
```
```bash
docker-compose build && docker-compose up
```

### Flask Server: 
Host port `8000` and Docker port `5000`

Links to call the service:
- [http://localhost:8000/](http://localhost:8000/)

- [Scrap sync](http://localhost:8000/scrap-sync)

- [Scrap async](http://localhost:8000/busca_fatura)

Ver browser em ação: http://localhost:7900/?autoconnect=1&resize=scale&password=secret

Selenium Grid UI: http://localhost:4444/ui/#





##  Selenium:
### UI
http://localhost:4444/ui/#
### Grid
http://localhost:7900/?autoconnect=1&resize=scale&password=secret    
