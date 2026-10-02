// Worker kirish nuqtasi. Mantiq `ilova.js` da (testlar uni soxta modullar
// bilan quradi); bu yerda faqat haqiqiy modullar ulanadi.
import { ilova } from "./ilova.js";
import * as xabar from "./xabar.js";
import * as vazifa from "./vazifa.js";
import * as dars from "./dars.js";

export default ilova({ xabar, vazifa, dars });
