import asyncio
from pyvdcapi.entities.vdc_host import VdcHost

async def main():
    host = VdcHost(name="Test Host", announce_service=False)
    await host.start()
    # create a test vDC so some properties exist
    host.create_vdc(name="testVdc", model="testModel", model_uid="testmodel")
    print("vDC host started, listening on port", host.port)
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    asyncio.run(main())
