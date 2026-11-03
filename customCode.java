package routines;

/*
 * user specification: the function's comment should contain keys as follows: 1. write about the function's comment.but
 * it must be before the "{talendTypes}" key.
 *
 * 2. {talendTypes} 's value must be talend Type, it is required . its value should be one of: String, char | Character,
 * long | Long, int | Integer, boolean | Boolean, byte | Byte, Date, double | Double, float | Float, Object, short |
 * Short
 *
 * 3. {Category} define a category for the Function. it is required. its value is user-defined .
 *
 * 4. {param} 's format is: {param} <type>[(<default value or closed list values>)] <name>[ : <comment>]
 *
 * <type> 's value should be one of: string, int, list, double, object, boolean, long, char, date. <name>'s value is the
 * Function's parameter name. the {param} is optional. so if you the Function without the parameters. the {param} don't
 * added. you can have many parameters for the Function.
 *
 * 5. {example} gives a example for the Function. it is optional.
 */
public class customCode {

    /**
     * helloExample: not return value, only print "hello" + message.
     *
     *
     * {talendTypes} String
     *
     * {Category} User Defined
     *
     * {param} string("world") input: The string need to be printed.
     *
     * {example} helloExemple("world") # hello world !.
     */
    public static void helloExample(String message) {
        if (message == null) {
            message = "World"; //$NON-NLS-1$
        }
        System.out.println("Hello " + message + " !"); //$NON-NLS-1$ //$NON-NLS-2$
    }
    /**
     *
     * getFormattedTime(long milliseconds)
     */
    public static String getFormattedTime(long milliseconds) {
    	int secs = (int) Math.round((double) milliseconds / 1000); // for millisecs arg instead of secs
        if (secs < 60)
            return secs + "s";
        else {
            int mins = (int) secs / 60;
            int remainderSecs = secs - (mins * 60);
            if (mins < 60) {
                return (mins < 10 ? "0" : "") + mins + "m "
                        + (remainderSecs < 10 ? "0" : "") + remainderSecs + "s";
            }
            else {
                int hours = (int) mins / 60;
                int remainderMins = mins - (hours * 60);
                return (hours < 10 ? "0" : "") + hours + "h "
                        + (remainderMins < 10 ? "0" : "") + remainderMins + "m "
                        + (remainderSecs < 10 ? "0" : "") + remainderSecs + "s";
            }
        }
    }
}
