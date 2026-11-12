# Lake labels

**Source:** ICIMOD ArcGIS REST service (HKH/GlacialLake, layers 1 and 2), fetched on <date>
via src/utils/fetch_icimod.py. Plus two manually added lakes (South Lhonak, Thame).

**Label 1:** lake ranked as potentially dangerous by ICIMOD (2015 imagery), or a lake that actually burst.
**Label 0:** lake in the 2015 inventory that is on no list. This means "unflagged", not "proven safe".

**Negative sampling:** 3 per positive, random seed 42, lakes below the 10th-percentile
size of dangerous lakes excluded. Area units: km^2.

**Not covered:** Bhutan and Sikkim dangerous-lake lists, and any region outside the
Koshi/Gandaki/Karnali basins.

**Known limits:** ICIMOD's ranking is based on lake, dam, glacier and surrounding
characteristics, so our classifier partly learns a remote-sensing rule. The only true
outcome labels are the two real bursts.