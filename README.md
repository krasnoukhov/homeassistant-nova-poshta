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
        url: https://novapost.com/mobileapp/
      title: >
        Посилки в поштоматі: {{ states("sensor.dmytro_delivered_parcels_in_kyiv_XXXX") }}шт
      message: >
        {{ state_attr("sensor.dmytro_delivered_parcels_in_kyiv_XXXX", "parcels") | join("\n") }}
mode: single
```

The `url` is what makes the notification open the Nova Post app when tapped on iOS. It has
to be an `https://` universal link: the companion app doesn't hand custom schemes off to
iOS, so `novapost://` silently does nothing
([home-assistant/iOS#4822](https://github.com/home-assistant/iOS/issues/4822)).
`https://novapost.com/mobileapp/` is claimed by the app's
[association file](https://novapost.com/.well-known/apple-app-site-association), so iOS
hands it to the app rather than opening the web page.

This also depends on the companion app's **Open links in** setting being Safari — with the
in-app browser, the link stays inside Home Assistant and the app never opens.

## Installation

### Via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=krasnoukhov&repository=homeassistant-nova-poshta&category=Integration)

* Search for "Nova Poshta" on HACS tab in Home Assistant
* Click on three dots and use the "Download" option
* Follow the steps
* Restart Home Assistant

### Manual Installation (not recommended)

* Copy the entire `custom_components/nova_poshta/` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant
