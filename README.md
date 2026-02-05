# Tapo Light Sync

Sync your TP-Link Tapo lights with Spotify album art in real time.

<p align="center">
  <img src="https://github.com/Sudeep10/tapolightsync/blob/main/demo.webp" alt="Demo"/>
</p>

## Supported Devices

| Device |
| ------ |
| L530   |
| L535   |
| L630   |
| L900   |
| L920   |
| L930   |

It uses [Tapo](https://github.com/mihai-dinculescu/tapo) to handle device connections, so the supported devices are same as devices supporting `set_hue_saturation`, you can check it here [Supported Devices](https://github.com/mihai-dinculescu/tapo/blob/main/SUPPORTED_DEVICES.md)

## Usage

1. Download the correct package for your system from the [Releases](https://github.com/Sudeep10/tapolightsync/releases/latest) page.
2. Create a `config.yaml` file (see the example here: [config.example.yaml](https://github.com/Sudeep10/tapolightsync/blob/main/config.example.yaml)).
3. Configure `config.yaml` as described below.
4. Run the app

## Configuration

### email and password

Write the email and password of your tapo account that is used to control the device through tapo app

Example

```yaml
email: email
password: password
```

### devices

You can add one or multiple devices that will handled by the application. To get the model name and ip address you can use the tapo app

`Open tapo app -> Select the device -> Click the settings button on top right corner -> Device info -> Model & IP address will be visible here`

Example

```yaml
devices:
  - type: L900
    ip: 192.168.0.1
  # if multiple devices
  - type: L900
    ip: 192.168.0.2
```

### spotify

login_type can be `oauth` or `connect`

#### Oauth (Recommended)

As of writing the readme, Spotify has temporarily restricted the creation of new developer applications, if you already have a application this method can be used

Steps to create spotify app

1. Go to the [Spotify dashboard](https://developer.spotify.com/dashboard/applications)
2. Click Create an app
3. You now can see your Client ID
4. Now click Edit Settings
5. Add http://localhost:8888/callback to the Redirect URIs
6. Scroll down and click Save

Open the config.yaml and set the login_type to oauth, add the client id and redirect_uri

Example

```yaml
spotify:
  login_type: oauth
  client_id: client_id
  redirect_uri: http://localhost:8888/callback
```

#### Connect

> [!WARNING]
> Connect method uses [SpotAPI](https://github.com/Aran404/SpotAPI) which uses spotify internal API, by using this method you agree with the risk mentioned here [NOTICE](https://github.com/Aran404/SpotAPI/blob/main/LEGAL_NOTICE.md)

This method does not require a Spotify developer application, instead it uses spotify cookies

`Open the browser where spotify is logged -> Press F12 or Ctrl + Shift + I (whichever works) -> Select Application in top bar -> Select Cookies then https://open.spotify.com -> There you will see the sp_dc & sp_t cookies value`

Open the config.yaml and set the login_type to connect, add spotify email, sp_dc and sp_t cookies value

Example

```yaml
spotify:
  login_type: connect
  sp_dc:
  sp_t:
  email:
```

## App Configuration

### app_config

| Key              | Type | Default | Accepted Value | Description                                    |
| ---------------- | ---- | ------- | -------------- | ---------------------------------------------- |
| off_on_pause<br> | bool | true    | true/false     | Turns off the lights when the music is paused  |
| off_on_stop      | bool | true    | true/false     | Turns off the lights when the music is stopped |

## Running the source

1. Download or clone the repo
2. Open the terminal in that directory

### Using uv

3. Run `uv sync`
4. Activate the virtual environment:
   - Linux/macOS: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
5. Create `config.yaml`
6. Run `python main.py`

### Using pip

3. Create a virtual env `python -m venv .venv`
4. Activate the virtual environment:
   - Linux/macOS: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
5. Run `pip install .`
6. Create config.yaml
7. Run `python main.py`

## Disclaimer

> This project is not affiliated with, endorsed by, or sponsored by Spotify or TP-Link.
> Use of Spotify internal APIs (via the Connect method) may violate Spotify’s Terms of Service. Use at your own risk.
