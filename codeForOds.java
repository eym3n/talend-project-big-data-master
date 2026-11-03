//Code java utilisé dans les jobs  jOdsCategorie, jOdsClient, jOdsProduit, jOdsSousCategorie, jOdsTypeClient, jOdsVente
//tJava_1
System.out.println("-----------------------------------------------------------------------------");
System.out.println("Début d'exécution du job "+jobName+ "        : " +
TalendDate.formatDate("yyyy-MM-dd HH:mm:ss",new java.util.Date(((Long)globalMap.get("tChronometerStart_1_STARTTIME"))))
);
System.out.println("-----------------------------------------------------------------------------");


//tJava_2
System.out.println("Nombre de lignes reçues                       : "+((Integer)globalMap.get("tFileInputDelimited_1_NB_LINE")));

System.out.println("Nombre de lignes rejetées                     : "+((Integer)globalMap.get("tFilterRow_1_NB_LINE_REJECT")));
System.out.println("Nombre de lignes en double                    : "+((Integer)globalMap.get("tUniqRow_1_NB_DUPLICATES")));
System.out.println("-----------------------------------------------------------------------------");
System.out.println("Fin d'exécution du job "+jobName+ "          : "+
TalendDate.formatDate("yyyy-MM-dd HH:mm:ss",new java.util.Date(((Long)globalMap.get("tChronometerStop_1_STOPTIME")))
));

System.out.println("Durée totale d'exécution du job "+jobName+ " : "+
customCode.getFormattedTime(((Long)globalMap.get("tChronometerStop_1_DURATION"))) + "");
System.out.println("-----------------------------------------------------------------------------");



//Code java utilisé dans le job principal : jChargeODS
//tJava_1
System.out.println("Connexion Base de données OK");
System.out.println("-----------------------------------------------------------------------------");
System.out.println("Début d'exécution du job "+jobName+ " :" +
TalendDate.formatDate("yyyy-MM-dd HH:mm:ss",new java.util.Date(((Long)globalMap.get("tChronometerStart_1_STARTTIME"))))
);
System.out.println("-----------------------------------------------------------------------------");


//tJava_2
System.out.println("-----------------------------------------------------------------------------");
System.out.println("Fin d'exécution du job "+jobName+ "   :"+
TalendDate.formatDate("yyyy-MM-dd HH:mm:ss",new java.util.Date(((Long)globalMap.get("tChronometerStop_1_STOPTIME")))
));

System.out.println("Durée totale                        :" +
customCode.getFormattedTime(((Long)globalMap.get("tChronometerStop_1_DURATION"))) + "");
System.out.println("-----------------------------------------------------------------------------");

//Code java utilisé dans les jobs  jDwhClient, jDwhProduit, jDwhVente, jChargeDWH
//tJava_1
System.out.println("-----------------------------------------------------------------------------");
System.out.println("Début d'exécution du job "+jobName+ "        : " +
TalendDate.formatDate("yyyy-MM-dd HH:mm:ss",new java.util.Date(((Long)globalMap.get("tChronometerStart_1_STARTTIME"))))
);


//tJava_2
System.out.println("Fin d'exécution du job "+jobName+ "          : "+
TalendDate.formatDate("yyyy-MM-dd HH:mm:ss",new java.util.Date(((Long)globalMap.get("tChronometerStop_1_STOPTIME")))
));

System.out.println("Durée totale d'exécution du job "+jobName+ " : "+
customCode.getFormattedTime(((Long)globalMap.get("tChronometerStop_1_DURATION"))) + "");
System.out.println("-----------------------------------------------------------------------------");