WORKOUT_LIBRARY = {

    "Recovery": [

        {
            "name": "Recovery 45",
            "steps": [
                {"duration": 45, "ftp": 50, "rpe": 2}
            ]
        },

        {
            "name": "Recovery 60",
            "steps": [
                {"duration": 60, "ftp": 52, "rpe": 2}
            ]
        }

    ],


    "Endurance": [

        {
            "name": "Endurance 90",
            "steps": [
                {"duration": 90, "ftp": 65, "rpe": 4}
            ]
        },

        {
            "name": "Endurance 2h",
            "steps": [
                {"duration": 120, "ftp": 68, "rpe": 4}
            ]
        },

        {
            "name": "Endurance 3h",
            "steps": [
                {"duration": 180, "ftp": 70, "rpe": 5}
            ]
        }

    ],


    "Tempo": [

        {
            "name": "Tempo 3x20",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 20, "ftp": 85, "rpe": 6},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 20, "ftp": 85, "rpe": 6},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 20, "ftp": 85, "rpe": 6},

                {"duration": 5, "ftp": 55, "rpe": 2}

            ]
        },


        {
            "name": "Sweet Spot 3x15",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 15, "ftp": 92, "rpe": 7},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 15, "ftp": 92, "rpe": 7},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 15, "ftp": 92, "rpe": 7},

                {"duration": 10, "ftp": 55, "rpe": 2}

            ]
        }

    ],


    "Threshold": [

        {
            "name": "2x20 FTP",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 20, "ftp": 100, "rpe": 8},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 20, "ftp": 100, "rpe": 8},

                {"duration": 25, "ftp": 55, "rpe": 2}

            ]
        },


        {
            "name": "3x15 FTP",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 15, "ftp": 100, "rpe": 8},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 15, "ftp": 100, "rpe": 8},
                {"duration": 5, "ftp": 55, "rpe": 2},

                {"duration": 15, "ftp": 100, "rpe": 8},

                {"duration": 15, "ftp": 55, "rpe": 2}

            ]
        },


        {
            "name": "Over Unders",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 2, "ftp": 105, "rpe": 8},
                {"duration": 2, "ftp": 95, "rpe": 7},

                {"duration": 2, "ftp": 105, "rpe": 8},
                {"duration": 2, "ftp": 95, "rpe": 7},

                {"duration": 2, "ftp": 105, "rpe": 8},
                {"duration": 2, "ftp": 95, "rpe": 7},

                {"duration": 2, "ftp": 105, "rpe": 8},
                {"duration": 2, "ftp": 95, "rpe": 7},

                {"duration": 20, "ftp": 55, "rpe": 2}

            ]
        }

    ],


    "VO2 Max": [

        {
            "name": "5x5",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 5, "ftp": 120, "rpe": 9},
                {"duration": 3, "ftp": 50, "rpe": 2},

                {"duration": 5, "ftp": 120, "rpe": 9},
                {"duration": 3, "ftp": 50, "rpe": 2},

                {"duration": 5, "ftp": 120, "rpe": 9},
                {"duration": 3, "ftp": 50, "rpe": 2},

                {"duration": 5, "ftp": 120, "rpe": 9},
                {"duration": 3, "ftp": 50, "rpe": 2},

                {"duration": 5, "ftp": 120, "rpe": 9},

                {"duration": 10, "ftp": 55, "rpe": 2}

            ]
        },


        {
            "name": "6x3",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                *[
                    {"duration": 3, "ftp": 125, "rpe": 9},
                    {"duration": 3, "ftp": 50, "rpe": 2},
                ] * 6,

                {"duration": 10, "ftp": 55, "rpe": 2}

            ]
        },


        {
            "name": "30/30",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                *[
                    {"duration": 0.5, "ftp": 130, "rpe": 10},
                    {"duration": 0.5, "ftp": 50, "rpe": 2},
                ] * 20,

                {"duration": 10, "ftp": 55, "rpe": 2}

            ]
        },


        {
            "name": "4x8",
            "steps": [

                {"duration": 15, "ftp": 55, "rpe": 2},

                {"duration": 8, "ftp": 108, "rpe": 9},
                {"duration": 4, "ftp": 50, "rpe": 2},

                {"duration": 8, "ftp": 108, "rpe": 9},
                {"duration": 4, "ftp": 50, "rpe": 2},

                {"duration": 8, "ftp": 108, "rpe": 9},
                {"duration": 4, "ftp": 50, "rpe": 2},

                {"duration": 8, "ftp": 108, "rpe": 9},

                {"duration": 10, "ftp": 55, "rpe": 2}

            ]
        }

    ]

}