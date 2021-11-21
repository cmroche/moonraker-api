# 1.0.0 (2021-11-21)


### Bug Fixes

* Able to send and receive responses ([7fcd63f](https://github.com/cmroche/moonraker-api/commit/7fcd63fcb6516215db40da5b5053f4e281ba79aa))
* Control loop checks stop state ([15b004b](https://github.com/cmroche/moonraker-api/commit/15b004b408bae05fb1f4c6c1c3d7afa0925cfaef))
* Drop exception from notification handler ([f99a953](https://github.com/cmroche/moonraker-api/commit/f99a95308eefb6185d87092de901e106de75fe5e))
* Missing annotations import ([ef2503a](https://github.com/cmroche/moonraker-api/commit/ef2503ab00f83b53fb76cddb496b8f1c0f592ac2))
* Propagate ClientNotAuthorizedError to connect ([ca28a59](https://github.com/cmroche/moonraker-api/commit/ca28a59938daea219c87cb641dcb4a27cdd1ab52))
* Python 3.9 compat ([e83f9e9](https://github.com/cmroche/moonraker-api/commit/e83f9e9b67ea0a3819dbfe18e0cd177a0ca1fa09))
* Return value for MoonrakerClient.connect() ([8bf544b](https://github.com/cmroche/moonraker-api/commit/8bf544b66dd8ddf72155f5c9e6df246d6375eec9))
* Use of TypedDict ([6359a1a](https://github.com/cmroche/moonraker-api/commit/6359a1a70052fe7f49fedeaa83e9ec954e420600))
* Wrap RPC notifications into task ([848c139](https://github.com/cmroche/moonraker-api/commit/848c1394209a37b82fe7965e5b632697d9678fcc))


### Features

* Add authentication via API key ([0bb416a](https://github.com/cmroche/moonraker-api/commit/0bb416a8638bd22e96ae74190dc05e455683a047))
* Add notification handler ([d8d09b1](https://github.com/cmroche/moonraker-api/commit/d8d09b1522b926c24a4f71a98ba9357b8713b142))
* Add printer administration functions ([908682f](https://github.com/cmroche/moonraker-api/commit/908682f5236cfdddf636a7f485e483c77a354e2a))
* Add support for errors in rpc response ([132f6a2](https://github.com/cmroche/moonraker-api/commit/132f6a2e35f1d12b0894c28fb222652d8fe24554))
* Allow passing external aiohttp session ([a522e8b](https://github.com/cmroche/moonraker-api/commit/a522e8b090556ff0ea8869772e9df02c221bfbe4))
* Better result messages ([a561dd2](https://github.com/cmroche/moonraker-api/commit/a561dd29b284b3f8c77fc1612e7450d856985ae8))
* Client API connection handling ([0be83ba](https://github.com/cmroche/moonraker-api/commit/0be83ba4086177b737d2c40b1885518a384e7256))
* Improved run loop and exception handling ([516d03e](https://github.com/cmroche/moonraker-api/commit/516d03e97204160c4519e1b0a83c3df485156082))
* Remove module APIs, add call_method() ([2ee436c](https://github.com/cmroche/moonraker-api/commit/2ee436c14ebf22a777967001e0f5fdd3a2e0ec8a))
