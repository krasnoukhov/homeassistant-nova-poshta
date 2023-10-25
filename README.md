# Home Assistant Nova Poshta integration

The Nova Poshta integration allows you to track delivered parcels, exposed as sensor per warehouse.

## Highlights

### Track delivered parcels

- Supports multiple warehouses (post office, poshtomat, different cities)
- Separate integration for every person in the household

<img src="https://github.com/krasnoukhov/homeassistant-nova-poshta/assets/944286/9d41505b-087b-49b1-ad63-c84401096459" alt="sensors" width="400">
<br>
<img src="https://github.com/krasnoukhov/homeassistant-nova-poshta/assets/944286/c88a9f39-d2a3-441e-a501-c0223a0cc9b5" alt="sensors" width="400">

### Use the UI to set up integration

<img src="https://github.com/krasnoukhov/homeassistant-nova-poshta/assets/944286/ff42b312-6758-4c40-80b3-eed8cdda9596" alt="setup" width="400">

## Example automation

Here's what I use to get a notification when there's a parcel in poshtomat and I'm approaching home:

```yml
alias: Poshtomat
trigger:
  - platform: zone
    entity_id: person.krasnoukhov
    zone: zone.home
    event: enter
condition:
  - condition: numeric_state
    entity_id: sensor.dmytro_delivered_parcels_in_kyiv_XXXX
    above: 0
action:
  - alias: Send critical mobile app notification
    service: notify.mobile_app_dmytro_iphone
    data:
      data:
        push:
          sound:
            critical: 1
            name: default
      title: >
        Посилки в поштоматі: {{ states("sensor.dmytro_delivered_parcels_in_kyiv_XXXX") }}шт
      message: >
        {{ state_attr("sensor.dmytro_delivered_parcels_in_kyiv_XXXX", "parcels") | join("\n") }}
mode: single
```

## Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

### Via HACS
* Add this repo as a ["Custom repository"](https://hacs.xyz/docs/faq/custom_repositories/) with type "Integration"
* Click "Install" in the new "Nova Poshta" card in HACS.
* Install
* Restart Home Assistant

### Manual Installation (not recommended)
* Copy the entire `custom_components/nova_poshta/` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant
