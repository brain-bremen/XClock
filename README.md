Tools for Synchronizing Experimental Clocks in Neurophysiology
==============================================================

**Requirements**:
- Use a DAQ device to give out multiple (at least 2) different TTL clock signals with
  potentially different frequencies and precise timing
- Choose acquisition time or number of pulses
- Save timestamps of TTL pulses given out
- Check precision of timestamps
- Save metdata (animal id, session id, ...)

**Nice to have**:
- Start trigger via TTL input or network API?
- Allow triggering other systems via API (e.g. OpenEphys)
- Plot clock signals post-hoc?